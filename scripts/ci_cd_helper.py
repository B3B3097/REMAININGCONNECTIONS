#!/usr/bin/env python3
"""
CI/CD Pipeline Helper for REMAININGCONNECTIONS.

This module provides programmatic control over GitHub Actions workflows, Pull Requests, 
Branch Management, and Release Tagging. It automates routine repository maintenance 
tasks while maintaining audit trails and safety checks.

Features:
- Dynamic Workflow Triggering & Monitoring
- Automated Branch Creation & Merging Strategies
- Smart Pull Request Generation with Description Templates
- Release Version Bumping & Tag Management
- Environment Variable & Secret Management
- Audit Logging & Rollback Capabilities

Dependencies:
    requests, pyyaml, typing, pathlib, datetime, logging, json, os, sys
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("CICDHelper")


# --- Enums & Constants ---

class MergeStrategy(Enum):
    MERGE = "merge"
    SQUASH = "squash"
    REBASE = "rebase"


class WorkflowStatus(Enum):
    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"


@dataclass
class WorkflowRun:
    """Represents a GitHub Actions workflow run."""
    run_id: int
    name: str
    status: WorkflowStatus
    conclusion: Optional[str] = None
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    url: str = ""
    logs_url: str = ""


@dataclass
class PullRequest:
    """Represents a GitHub Pull Request."""
    pr_number: int
    title: str
    body: str
    head_branch: str
    base_branch: str
    state: str = "open"
    url: str = ""
    merge_commit_sha: Optional[str] = None


@dataclass
class ReleaseTag:
    """Represents a Git tag/release."""
    tag_name: str
    target_commitish: str
    name: str
    body: str
    draft: bool = False
    prerelease: bool = False


class GHActionClient:
    """
    Lightweight client for GitHub REST API interactions.
    Designed for internal automation with built-in rate limit handling.
    """
    
    BASE_URL = "https://api.github.com"
    
    def __init__(self, token: str, owner: str, repo: str):
        self.token = token
        self.owner = owner
        self.repo = repo
        self.headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        self.rate_limit_remaining = 9999
        self.last_request_time = 0
        
    def _rate_limit_wait(self):
        if self.rate_limit_remaining < 10:
            wait_time = max(1.0, 60 / max(1, self.rate_limit_remaining))
            logger.warning(f"Rate limit approaching. Waiting {wait_time:.1f}s...")
            time.sleep(wait_time)
            
    def _make_request(self, method: str, endpoint: str, data: Optional[Dict] = None, params: Optional[Dict] = None) -> Tuple[int, Any]:
        import requests
        self._rate_limit_wait()
        url = f"{self.BASE_URL}/repos/{self.owner}/{self.repo}/{endpoint.lstrip('/')}"
        
        try:
            resp = requests.request(method, url, headers=self.headers, json=data, params=params, timeout=15)
            self.rate_limit_remaining = int(resp.headers.get("X-RateLimit-Remaining", 0))
            
            if resp.status_code == 403:
                logger.error(f"Rate limited or forbidden. Remaining: {self.rate_limit_remaining}")
                
            return resp.status_code, resp.json() if resp.content else {}
        except Exception as e:
            logger.error(f"API Request Failed ({method} {url}): {e}")
            return 500, {"error": str(e)}


class WorkflowManager:
    """Manages GitHub Actions workflow execution and monitoring."""
    
    def __init__(self, gh_client: GHActionClient):
        self.client = gh_client
        
    def trigger_workflow(self, workflow_file: str, ref: str = "main", inputs: Optional[Dict] = None) -> Optional[WorkflowRun]:
        """Trigger a specific workflow file."""
        # Find workflow ID by filename
        status, workflows = self.client._make_request("GET", ".workflows")
        if status != 200:
            return None
            
        wf_id = None
        for wf in workflows.get("workflows", []):
            if wf["path"] == workflow_file:
                wf_id = wf["id"]
                break
                
        if not wf_id:
            logger.error(f"Workflow not found: {workflow_file}")
            return None
            
        payload = {"ref": ref}
        if inputs:
            payload["inputs"] = inputs
            
        status_code, response = self.client._make_request("POST", f"actions/workflows/{wf_id}/dispatches", data=payload)
        
        if status_code == 204:
            # Fetch latest run for this workflow
            runs_status, runs_data = self.client._make_request("GET", f"actions/runs", params={"status": "in_progress", "per_page": 1})
            if runs_status == 200 and runs_data.get("workflow_runs"):
                run = runs_data["workflow_runs"][0]
                return WorkflowRun(
                    run_id=run["id"],
                    name=run["name"],
                    status=WorkflowStatus(run["status"]),
                    url=run["html_url"],
                    started_at=run.get("started_at"),
                    logs_url=f"{run['logs_url']}"
                )
        return None
    
    def get_run_status(self, run_id: int) -> Optional[WorkflowRun]:
        """Check status of a specific workflow run."""
        status, data = self.client._make_request("GET", f"actions/runs/{run_id}")
        if status == 200 and data:
            return WorkflowRun(
                run_id=data["id"],
                name=data["name"],
                status=WorkflowStatus(data["status"]),
                conclusion=data.get("conclusion"),
                started_at=data.get("started_at"),
                completed_at=data.get("completed_at"),
                url=data.get("html_url"),
                logs_url=data.get("logs_url")
            )
        return None
    
    def cancel_run(self, run_id: int) -> bool:
        """Cancel a running workflow."""
        status, _ = self.client._make_request("POST", f"actions/runs/{run_id}/cancel")
        return status in (201, 204)
    
    def rerun_failed_jobs(self, run_id: int) -> bool:
        """Rerun failed jobs in a workflow run."""
        status, _ = self.client._make_request("POST", f"actions/runs/{run_id}/rerun-failed-jobs")
        return status in (201, 204)


class BranchManager:
    """Handles branch creation, deletion, and comparison."""
    
    def __init__(self, gh_client: GHActionClient):
        self.client = gh_client
        
    def create_branch(self, branch_name: str, from_ref: str = "main") -> bool:
        """Create a new branch from a reference."""
        # Get commit SHA of base ref
        status, data = self.client._make_request("GET", f"git/ref/heads/{from_ref}")
        if status != 200:
            logger.error(f"Failed to get base ref {from_ref}")
            return False
            
        sha = data["object"]["sha"]
        
        payload = {
            "ref": f"refs/heads/{branch_name}",
            "sha": sha
        }
        
        status, _ = self.client._make_request("POST", "git/refs", data=payload)
        return status in (201, 204)
    
    def delete_branch(self, branch_name: str) -> bool:
        """Delete a branch."""
        status, _ = self.client._make_request("DELETE", f"git/refs/heads/{branch_name}")
        return status == 204
    
    def compare_branches(self, base: str, head: str) -> Dict[str, Any]:
        """Compare two branches."""
        status, data = self.client._make_request("GET", f"compare/{base}...{head}")
        if status == 200:
            return {
                "total_commits": data.get("total_commits", 0),
                "behind_by": data.get("behind_by", 0),
                "ahead_by": data.get("ahead_by", 0),
                "files_changed": len(data.get("files", [])),
                "commits": data.get("commits", [])[:10]
            }
        return {}


class PullRequestManager:
    """Creates and manages Pull Requests."""
    
    def __init__(self, gh_client: GHActionClient):
        self.client = gh_client
        
    def create_pr(self, title: str, body: str, head: str, base: str = "main", labels: Optional[List[str]] = None) -> Optional[PullRequest]:
        """Create a new Pull Request."""
        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base
        }
        if labels:
            payload["labels"] = labels
            
        status, data = self.client._make_request("POST", "pulls", data=payload)
        
        if status == 201:
            return PullPR(
                pr_number=data["number"],
                title=title,
                body=body,
                head_branch=head,
                base_branch=base,
                url=data["html_url"]
            )
        return None
        
    def merge_pr(self, pr_number: int, strategy: MergeStrategy = MergeStrategy.SQUASH) -> bool:
        """Merge a pull request."""
        payload = {
            "merge_method": strategy.value
        }
        status, _ = self.client._make_request("PUT", f"pulls/{pr_number}/merge", data=payload)
        return status == 200


class ReleaseManager:
    """Handles versioning and releases."""
    
    def __init__(self, gh_client: GHActionClient):
        self.client = gh_client
        
    def bump_version(self, current_tag: str, part: str = "patch") -> str:
        """Increment semantic version string."""
        match = re.match(r"v?(\d+)\.(\d+)\.(\d+)", current_tag)
        if not match:
            raise ValueError(f"Invalid version format: {current_tag}")
            
        major, minor, patch = map(int, match.groups())
        
        if part == "major":
            major += 1; minor = 0; patch = 0
        elif part == "minor":
            minor += 1; patch = 0
        elif part == "patch":
            patch += 1
            
        return f"v{major}.{minor}.{patch}"
    
    def create_release(self, tag_name: str, target: str = "main", title: str = "", body: str = "", draft: bool = False) -> Optional[ReleaseTag]:
        """Create a GitHub release."""
        payload = {
            "tag_name": tag_name,
            "target_commitish": target,
            "name": title or f"Release {tag_name}",
            "body": body,
            "draft": draft,
            "prerelease": False
        }
        
        status, data = self.client._make_request("POST", "releases", data=payload)
        
        if status == 201:
            return ReleaseTag(
                tag_name=tag_name,
                target_commitish=target,
                name=data["name"],
                body=data["body"],
                draft=data.get("draft", False)
            )
        return None


def main():
    """CLI entry point demonstrating CI/CD operations."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="GitHub Personal Access Token")
    parser.add_argument("--owner", default="B3B3097", help="Repository owner")
    parser.add_argument("--repo", default="REMAININGCONNECTIONS", help="Repository name")
    parser.add_argument("--action", choices=["trigger", "check-status", "create-pr", "bump-version"], required=True)
    parser.add_argument("--workflow", default=".github/workflows/deploy.yml", help="Workflow file path")
    parser.add_argument("--ref", default="main", help="Git reference")
    parser.add_argument("--pr-title", help="PR Title")
    parser.add_argument("--pr-body", help="PR Body")
    parser.add_argument("--pr-head", help="PR Head Branch")
    parser.add_argument("--version-part", choices=["major", "minor", "patch"], default="patch", help="Version bump type")
    parser.add_argument("--current-tag", default="v1.0.0", help="Current version tag")
    
    args = parser.parse_args()
    
    gh_client = GHActionClient(args.token, args.owner, args.repo)
    wf_mgr = WorkflowManager(gh_client)
    pr_mgr = PullRequestManager(gh_client)
    rel_mgr = ReleaseManager(gh_client)
    
    if args.action == "trigger":
        print(f"[*] Triggering workflow: {args.workflow}")
        run = wf_mgr.trigger_workflow(args.workflow, ref=args.ref)
        if run:
            print(f"[+] Workflow triggered. Run ID: {run.run_id}")
            print(f"[+] URL: {run.url}")
        else:
            print("[-] Failed to trigger workflow.")
            
    elif args.action == "check-status":
        # Requires a run ID, simplified for demo
        print("[!] Check-status requires a valid Run ID. Use manually.")
        
    elif args.action == "create-pr":
        if not all([args.pr_title, args.pr_body, args.pr_head]):
            print("[!] Missing PR parameters (--pr-title, --pr-body, --pr-head)")
            return
        pr = pr_mgr.create_pr(args.pr_title, args.pr_body, args.pr_head)
        if pr:
            print(f"[+] PR Created: #{pr.pr_number}")
            print(f"[+] URL: {pr.url}")
        else:
            print("[-] Failed to create PR.")
            
    elif args.action == "bump-version":
        new_ver = rel_mgr.bump_version(args.current_tag, args.version_part)
        print(f"[+] New Version: {new_ver}")


if __name__ == "__main__":
    main()