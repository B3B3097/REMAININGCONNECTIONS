#!/usr/bin/env python3
"""Probe subscription configs through Xray core for real connectivity validation."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
from pathlib import Path
from typing import Any

from strict_proxy_checker import check_xray_uri, utc_timestamp
from subscription_validator import validate_subscription_content


def uri_lines(text: str) -> list[str]:
    """Extract all proxy URI lines from text content."""
    uri_protocols = {
        "vless", "vmess", "ss", "ssr", "trojan", "trojan-go",
        "hysteria", "hysteria2", "hy2", "tuic", "wireguard", "wg",
    }
    pattern = re.compile(
        r"(?im)^\s*((?:" + "|".join(re.escape(p) for p in uri_protocols) + r")://[^\s#]+(?:#[^\r\n]*)?)\s*$"
    )
    return [match.group(1).strip() for match in pattern.finditer(text)]


def load_subscriptions(path: Path) -> list[dict[str, Any]]:
    """Load subscription list from JSON file."""
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        subs = data.get("subscriptions", [])
        return subs if isinstance(subs, list) else []
    except (OSError, json.JSONDecodeError):
        return []


async def probe_one(
    item: dict[str, Any],
    timeout: float,
    nodes_per_subscription: int,
) -> dict[str, Any]:
    """Probe one subscription: validate content and test configs through Xray."""
    url = item.get("url", "")
    content = item.get("content", "")
    
    # Validate subscription content structure
    validation = validate_subscription_content(content, url)
    item["validation"] = validation
    
    # Extract URIs for Xray probing
    nodes = uri_lines(content)
    total_nodes = len(nodes)
    item["total_configs"] = total_nodes
    
    # Limit nodes to probe
    nodes_to_probe = nodes[:nodes_per_subscription]
    
    if not nodes_to_probe:
        item["status"] = "unverified" if validation["valid"] else "invalid"
        item["xray_probe"] = {
            "status": "unverified" if validation["valid"] else "invalid",
            "reason": (
                "structured_config_requires_format_conversion"
                if validation["valid"]
                else "no_supported_config_to_probe"
            ),
            "checked_at": utc_timestamp(),
        }
        return item
    
    # Probe all extracted configs through Xray
    semaphore = asyncio.Semaphore(10)
    
    async def check_one_uri(uri: str) -> dict[str, Any]:
        async with semaphore:
            result = await check_xray_uri(uri, timeout)
            return {
                "uri": uri[:100] + "..." if len(uri) > 100 else uri,
                "status": result.status,
                "verification": result.verification,
                "latency_ms": result.latency_ms,
                "error": result.error,
            }
    
    probe_results = await asyncio.gather(
        *(check_one_uri(uri) for uri in nodes_to_probe),
        return_exceptions=True,
    )
    
    # Analyze results
    working = [r for r in probe_results if isinstance(r, dict) and r["status"] == "working"]
    failed = [r for r in probe_results if isinstance(r, dict) and r["status"] != "working"]
    errors = [r for r in probe_results if isinstance(r, Exception)]
    
    item["xray_probe"] = {
        "checked_at": utc_timestamp(),
        "total_probed": len(nodes_to_probe),
        "working_count": len(working),
        "failed_count": len(failed),
        "error_count": len(errors),
        "working_configs": working[:5],  # Top 5 working
        "failed_configs": failed[:3],  # Sample failures
    }
    
    # Set overall status
    if len(working) > 0:
        item["status"] = "working"
        item["working_ratio"] = round(len(working) / len(nodes_to_probe), 3)
    elif len(failed) > 0:
        item["status"] = "degraded"
    else:
        item["status"] = "invalid"
    
    # Calculate average latency for working configs
    latencies = [r["latency_ms"] for r in working if r.get("latency_ms")]
    if latencies:
        item["avg_latency_ms"] = round(sum(latencies) / len(latencies), 2)
    
    return item


async def probe_all(
    subscriptions: list[dict[str, Any]],
    timeout: float,
    nodes_per_subscription: int,
    max_subscriptions: int,
) -> list[dict[str, Any]]:
    """Probe multiple subscriptions with error handling."""
    
    async def guarded(item: dict[str, Any]) -> dict[str, Any]:
        try:
            return await probe_one(item, timeout, nodes_per_subscription)
        except Exception as exc:
            item["status"] = "error"
            item["xray_probe"] = {
                "status": "error",
                "error": f"{type(exc).__name__}: {str(exc)[:200]}",
                "checked_at": utc_timestamp(),
            }
            return item
    
    # Probe limited number of subscriptions
    probe_targets = subscriptions[:max_subscriptions]
    checked = await asyncio.gather(*(guarded(item) for item in probe_targets))
    
    # Return probed + unchecked subscriptions
    return checked + subscriptions[max_subscriptions:]


def build_payload(
    subscriptions: list[dict[str, Any]],
    timeout: float,
    nodes_per_subscription: int,
) -> dict[str, Any]:
    """Build output JSON payload with statistics."""
    working = [s for s in subscriptions if s.get("status") == "working"]
    degraded = [s for s in subscriptions if s.get("status") == "degraded"]
    invalid = [s for s in subscriptions if s.get("status") == "invalid"]
    
    # Sort by working status and latency
    subscriptions.sort(
        key=lambda s: (
            s.get("status") != "working",
            s.get("status") != "degraded",
            s.get("avg_latency_ms") if s.get("avg_latency_ms") else float("inf"),
            -s.get("working_ratio", 0),
        )
    )
    
    return {
        "generated_at": utc_timestamp(),
        "generator": "scripts/probe_subscription_configs.py",
        "telegram_channel": "https://t.me/REMAININGCONNECTIONS",
        "total_subscriptions": len(subscriptions),
        "working_count": len(working),
        "degraded_count": len(degraded),
        "invalid_count": len(invalid),
        "probe_timeout_seconds": timeout,
        "nodes_per_subscription": nodes_per_subscription,
        "verification_method": "xray_core_real_connection",
        "subscriptions": subscriptions,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        default="extracted/subscriptions_extracted.json",
        help="Input JSON with subscription content",
    )
    parser.add_argument(
        "--output",
        default="checked/subscriptions_probed.json",
        help="Output JSON with Xray probe results",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("XRAY_PROBE_TIMEOUT", "8")),
        help="Timeout per config probe (seconds)",
    )
    parser.add_argument(
        "--nodes-per-sub",
        type=int,
        default=int(os.getenv("NODES_PER_SUBSCRIPTION", "50")),
        help="Max configs to probe per subscription",
    )
    parser.add_argument(
        "--max-subscriptions",
        type=int,
        default=int(os.getenv("MAX_PROBE_SUBSCRIPTIONS", "100")),
        help="Max subscriptions to probe",
    )
    args = parser.parse_args()
    
    subscriptions = load_subscriptions(Path(args.input))
    print(f"Loaded {len(subscriptions)} subscriptions")
    
    timeout = max(2.0, args.timeout)
    nodes_per_sub = max(1, args.nodes_per_sub)
    max_subs = max(1, args.max_subscriptions)
    
    print(f"Probing up to {max_subs} subscriptions...")
    print(f"Testing up to {nodes_per_sub} configs per subscription")
    print(f"Timeout: {timeout}s per config")
    
    subscriptions = asyncio.run(
        probe_all(subscriptions, timeout, nodes_per_sub, max_subs)
    )
    
    payload = build_payload(subscriptions, timeout, nodes_per_sub)
    
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    
    print(f"\nResults:")
    print(f"  Working: {payload['working_count']}")
    print(f"  Degraded: {payload['degraded_count']}")
    print(f"  Invalid: {payload['invalid_count']}")
    print(f"  Total: {payload['total_subscriptions']}")
    print(f"\nSaved to: {args.output}")


if __name__ == "__main__":
    main()