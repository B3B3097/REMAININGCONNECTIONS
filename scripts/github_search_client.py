#!/usr/bin/env python3
"""
Advanced GitHub Search Client for REMAININGCONNECTIONS.

Provides high-level abstractions for searching repositories, users, 
and code snippets on GitHub. Includes rate limit handling, caching,
and intelligent query generation.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple
from urllib.parse import quote_plus

try:
    import aiohttp
except ImportError:
    aiohttp = None

logger = logging.getLogger("GitHubClient")


@dataclass
class SearchStats:
    """Statistics about a search operation."""
    total_results: int = 0
    repos_found: int = 0
    files_scanned: int = 0
    queries_executed: int = 0
    errors: int = 0
    rate_limit_remaining: int = 0


class GitHubRateLimiter:
    """Manages GitHub API rate limits."""

    def __init__(self):
        self.last_request_time = 0
        self.min_delay = 0.2  # seconds between requests to be safe

    async def wait_if_needed(self):
        """Wait if necessary to avoid rate limiting."""
        now = time.time()
        elapsed = now - self.last_request_time
        if elapsed < self.min_delay:
            await asyncio.sleep(self.min_delay - elapsed)
        self.last_request_time = time.time()


class GitHubSearchClient:
    """
    Asynchronous client for GitHub Search API.
    
    Features:
    - Keyword search for repositories.
    - Code search within repositories.
    - User search.
    - Intelligent retry logic.
    - Rate limit awareness.
    """

    BASE_URL = "https://api.github.com"
    USER_AGENT = "REMAININGCONNECTIONS-SEARCHER/1.0"

    def __init__(self, token: Optional[str] = None, max_concurrency: int = 5):
        self.token = token
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": self.USER_AGENT,
        }
        if token:
            self.headers["Authorization"] = f"token {token}"
        
        self.rate_limiter = GitHubRateLimiter()
        self.session: Optional[aiohttp.ClientSession] = None
        self.max_concurrency = max_concurrency
        
        # Caching
        self.repo_cache: Dict[str, Dict] = {}
        self.search_cache: Dict[str, List] = {}

    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session."""
        if self.session is None or self.session.closed:
            timeout = aiohttp.ClientTimeout(total=10)
            self.session = aiohttp.ClientSession(
                headers=self.headers,
                timeout=timeout
            )
        return self.session

    async def close(self):
        """Close the HTTP session."""
        if self.session and not self.session.closed:
            await self.session.close()

    async def search_repos(self, query: str, sort: str = "stars", order: str = "desc", per_page: int = 30) -> Tuple[List[Dict], SearchStats]:
        """
        Search for repositories.
        
        Args:
            query: GitHub search query string.
            sort: Sort by (stars, forks, updated).
            order: Order (asc, desc).
            per_page: Results per page (max 100).
            
        Returns:
            Tuple of (list of repo dicts, search stats).
        """
        if not aiohttp:
            logger.error("aiohttp is required for GitHubSearchClient.")
            return [], SearchStats(errors=1)

        await self.rate_limiter.wait_if_needed()
        
        url = f"{self.BASE_URL}/search/repositories"
        params = {
            "q": query,
            "sort": sort,
            "order": order,
            "per_page": min(per_page, 100),
        }
        
        stats = SearchStats()
        repos = []
        
        try:
            async with self._get_session() as session:
                async with session.get(url, params=params) as resp:
                    stats.rate_limit_remaining = int(resp.headers.get("X-RateLimit-Remaining", 0))
                    
                    if resp.status == 403:
                        logger.warning("Rate limit exceeded or IP banned.")
                        stats.errors += 1
                        return repos, stats
                    
                    if resp.status != 200:
                        logger.error(f"Failed to fetch repos: {resp.status}")
                        stats.errors += 1
                        return repos, stats
                        
                    data = await resp.json()
                    stats.total_results = data.get("total_count", 0)
                    items = data.get("items", [])
                    
                    for item in items:
                        repo_info = {
                            "name": item["full_name"],
                            "description": item.get("description"),
                            "stars": item.get("stargazers_count", 0),
                            "forks": item.get("forks_count", 0),
                            "language": item.get("language"),
                            "updated_at": item.get("updated_at"),
                            "url": item.get("html_url")
                        }
                        repos.append(repo_info)
                        self.repo_cache[item["full_name"]] = repo_info
                        
        except Exception as e:
            logger.error(f"Error searching repos for '{query}': {e}")
            stats.errors += 1
            
        stats.repos_found = len(repos)
        stats.queries_executed += 1
        
        return repos, stats

    async def search_code(self, query: str, per_page: int = 10) -> Tuple[List[Dict], SearchStats]:
        """
        Search for code snippets.
        
        Args:
            query: Code search query.
            per_page: Max results.
        """
        if not aiohttp:
            return [], SearchStats(errors=1)

        await self.rate_limiter.wait_if_needed()

        url = f"{self.BASE_URL}/search/code"
        params = {
            "q": query,
            "per_page": min(per_page, 100),
        }
        
        stats = SearchStats()
        results = []
        
        try:
            async with self._get_session() as session:
                async with session.get(url, params=params) as resp:
                    stats.rate_limit_remaining = int(resp.headers.get("X-RateLimit-Remaining", 0))
                    
                    if resp.status == 403:
                        logger.warning("Rate limit exceeded for code search.")
                        stats.errors += 1
                        return results, stats
                        
                    if resp.status != 200:
                        logger.error(f"Code search failed: {resp.status}")
                        stats.errors += 1
                        return results, stats
                        
                    data = await resp.json()
                    stats.total_results = data.get("total_count", 0)
                    items = data.get("items", [])
                    
                    for item in items:
                        result = {
                            "name": item.get("name"),
                            "path": item.get("path"),
                            "repository": item.get("repository", {}).get("full_name"),
                            "html_url": item.get("html_url"),
                            "score": item.get("score")
                        }
                        results.append(result)
                        
        except Exception as e:
            logger.error(f"Error searching code for '{query}': {e}")
            stats.errors += 1
            
        stats.files_scanned = len(results)
        stats.queries_executed += 1
        
        return results, stats

    async def get_repo_contents(self, owner: str, repo: str, path: str = "", ref: str = "main") -> Tuple[List[Dict], SearchStats]:
        """
        Get contents of a repository directory.
        
        Args:
            owner: Repository owner.
            repo: Repository name.
            path: Directory path inside repo.
            ref: Branch or commit SHA.
        """
        if not aiohttp:
            return [], SearchStats(errors=1)

        await self.rate_limiter.wait_if_needed()

        url = f"{self.BASE_URL}/repos/{owner}/{repo}/contents/{path}"
        params = {"ref": ref}
        
        stats = SearchStats()
        contents = []
        
        try:
            async with self._get_session() as session:
                async with session.get(url, params=params) as resp:
                    if resp.status == 404:
                        return [], stats # Not found is not an error for navigation
                    
                    if resp.status != 200:
                        logger.error(f"Failed to get contents of {owner}/{repo}/{path}: {resp.status}")
                        stats.errors += 1
                        return contents, stats
                        
                    data = await resp.json()
                    if isinstance(data, list):
                        for item in data:
                            content_info = {
                                "name": item["name"],
                                "path": item["path"],
                                "type": item["type"], # file or dir
                                "size": item.get("size"),
                                "download_url": item.get("download_url"),
                                "sha": item.get("sha")
                            }
                            contents.append(content_info)
                            
        except Exception as e:
            logger.error(f"Error getting contents: {e}")
            stats.errors += 1
            
        stats.queries_executed += 1
        
        return contents, stats

    async def get_file_content(self, owner: str, repo: str, path: str, ref: str = "main") -> Optional[str]:
        """
        Get raw content of a specific file.
        """
        if not aiohttp:
            return None
            
        contents, _ = await self.get_repo_contents(owner, repo, path, ref)
        if not contents:
            return None
            
        file_info = contents[0] # Should be only one if path is exact
        download_url = file_info.get("download_url")
        
        if not download_url:
            return None
            
        try:
            async with self._get_session() as session:
                async with session.get(download_url) as resp:
                    if resp.status == 200:
                        return await resp.text()
                    else:
                        return None
        except Exception as e:
            logger.error(f"Error fetching file {path}: {e}")
            return None


def main():
    """CLI for quick GitHub searches."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", help="GitHub Token (optional)")
    parser.add_argument("--action", choices=["repos", "code"], required=True, help="Action to perform")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--limit", type=int, default=5, help="Max results")
    
    args = parser.parse_args()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    client = GitHubSearchClient(token=args.token)
    
    try:
        if args.action == "repos":
            print(f"[*] Searching repos for: {args.query}")
            repos, stats = loop.run_until_complete(client.search_repos(args.query, per_page=args.limit))
            print(f"[+] Found {stats.repos_found} repos out of {stats.total_results}")
            for r in repos:
                print(f"  - {r['name']} ({r['stars']} stars)")
                
        elif args.action == "code":
            print(f"[*] Searching code for: {args.query}")
            results, stats = loop.run_until_complete(client.search_code(args.query, per_page=args.limit))
            print(f"[+] Found {stats.files_scanned} matches out of {stats.total_results}")
            for r in results:
                print(f"  - {r['repository']}/{r['path']}")
                
    finally:
        loop.run_until_complete(client.close())
        loop.close()


if __name__ == "__main__":
    main()