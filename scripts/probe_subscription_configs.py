#!/usr/bin/env python3
"""Probe subscription configs through Xray core for real connectivity validation."""

from __future__ import annotations

import argparse
import asyncio
import json
import re
from pathlib import Path
from typing import Any

from strict_proxy_checker import check_xray_uri, utc_timestamp
from subscription_validator import validate_subscription


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
    validation = validate_subscription(content)
    item["validation"] = validation
    
    if not validation["valid"]:
        item["status"] = "invalid"
        item["total_configs"] = 0
        item["working_configs"] = 0
        item["checked_at"] = utc_timestamp()
        return item
    
    # Extract URIs for Xray probing
    nodes = uri_lines(content)
    total_nodes = len(nodes)
    item["total_configs"] = total_nodes
    
    # Limit nodes to probe
    nodes_to_probe = nodes[:nodes_per_subscription]
    
    if not nodes_to_probe:
        item["status"] = "empty"
        item["working_configs"] = 0
        item["checked_at"] = utc_timestamp()
        return item
    
    # Probe each node through Xray
    working_count = 0
    probe_results = []
    
    for uri in nodes_to_probe:
        result = await check_xray_uri(uri, timeout)
        if result.get("xray_ok"):
            working_count += 1
        probe_results.append({
            "uri": uri[:100],  # Truncate for storage
            "xray_ok": result.get("xray_ok", False),
            "error": result.get("error"),
        })
    
    item["working_configs"] = working_count
    item["probed_sample"] = len(nodes_to_probe)
    item["probe_results"] = probe_results[:10]  # Keep only first 10 results
    
    # Set status based on working configs
    if working_count > 0:
        item["status"] = "working"
    else:
        item["status"] = "failed"
    
    item["checked_at"] = utc_timestamp()
    return item


async def probe_all(
    subscriptions: list[dict[str, Any]],
    timeout: float,
    concurrency: int,
    nodes_per_subscription: int,
) -> list[dict[str, Any]]:
    """Probe all subscriptions with concurrency control."""
    semaphore = asyncio.Semaphore(max(1, concurrency))
    
    async def probe_with_semaphore(sub: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await probe_one(sub, timeout, nodes_per_subscription)
    
    tasks = [probe_with_semaphore(sub) for sub in subscriptions]
    return await asyncio.gather(*tasks)


async def main_async(args: argparse.Namespace) -> None:
    """Main async entry point."""
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    subscriptions = load_subscriptions(input_path)
    if not subscriptions:
        print("[!] No subscriptions to probe.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                {"subscriptions": [], "generated_at": utc_timestamp()},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        return
    
    max_probe = args.max_probe
    to_probe = subscriptions[:max_probe] if max_probe > 0 else subscriptions
    
    print(f"[*] Probing {len(to_probe)} subscriptions...")
    print(f"[*] Settings: timeout={args.timeout}s, concurrency={args.concurrency}")
    print(f"[*] Testing up to {args.nodes_per_sub} nodes per subscription")
    
    probed = await probe_all(
        to_probe,
        args.timeout,
        args.concurrency,
        args.nodes_per_sub,
    )
    
    # Filter out invalid subscriptions
    valid_subscriptions = [
        sub for sub in probed 
        if sub.get("validation", {}).get("valid", False)
    ]
    
    working = [sub for sub in valid_subscriptions if sub.get("status") == "working"]
    
    print(f"[+] Probed {len(probed)} subscriptions.")
    print(f"[+] Valid: {len(valid_subscriptions)}, Working: {len(working)}")
    
    # Save only valid subscriptions
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {
                "subscriptions": valid_subscriptions,
                "generated_at": utc_timestamp(),
                "summary": {
                    "total": len(valid_subscriptions),
                    "working": len(working),
                    "failed": len([s for s in valid_subscriptions if s.get("status") == "failed"]),
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[+] Wrote {output_path}")


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Probe subscription configs through Xray core"
    )
    parser.add_argument(
        "--input",
        default="extracted/subscriptions_extracted.json",
        help="Input JSON file with extracted subscriptions",
    )
    parser.add_argument(
        "--output",
        default="data/subscriptions_found.json",
        help="Output JSON file with probed subscriptions",
    )
    parser.add_argument(
        "--max-probe",
        type=int,
        default=100,
        help="Maximum subscriptions to probe (0 = all)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout for each Xray connectivity check",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=5,
        help="Concurrency limit for probing",
    )
    parser.add_argument(
        "--nodes-per-sub",
        type=int,
        default=5,
        help="Number of nodes to test per subscription",
    )
    args = parser.parse_args()
    
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()