#!/usr/bin/env python3
"""Strictly probe representative URI nodes from discovered subscriptions through Xray."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

import requests

from strict_proxy_checker import check_xray_uri, utc_timestamp
from subscription_validator import validate_subscription_content


def fetch_subscription(url: str, timeout: float) -> str | None:
    try:
        response = requests.get(
            url,
            timeout=(5, timeout),
            headers={"User-Agent": os.getenv("USER_AGENT", "REMAININGCONNECTIONS/1.0")},
            allow_redirects=True,
        )
        if response.status_code != 200 or not response.content:
            return None
        if len(response.content) > 2_000_000:
            return None
        return response.content.decode(response.encoding or "utf-8", errors="replace")
    except requests.RequestException:
        return None


def uri_lines(content: str) -> list[str]:
    decoded = validate_subscription_content(content)
    effective = content
    if decoded["format"] == "base64_uri_list":
        import base64

        compact = "".join(content.split())
        compact += "=" * (-len(compact) % 4)
        effective = base64.urlsafe_b64decode(compact).decode("utf-8-sig", errors="replace")
    result: list[str] = []
    for line in effective.splitlines():
        value = line.strip()
        if "://" not in value:
            continue
        scheme = value.split("://", 1)[0].lower()
        if scheme in {"vless", "vmess", "ss", "shadowsocks", "trojan", "hysteria2", "hy2", "tuic"}:
            result.append(value)
    return list(dict.fromkeys(result))


async def probe_item(item: dict[str, Any], timeout: float, nodes_per_subscription: int) -> dict[str, Any]:
    url = item.get("subscription_url")
    if not isinstance(url, str) or not url.startswith(("https://", "http://")):
        item["xray_probe"] = {"status": "skipped", "reason": "missing_subscription_url"}
        return item

    content = await asyncio.to_thread(fetch_subscription, url, timeout)
    if content is None:
        item["status"] = "invalid"
        item["xray_probe"] = {"status": "invalid", "reason": "download_failed", "checked_at": utc_timestamp()}
        return item

    validation = validate_subscription_content(content, item.get("config_path", ""))
    item.update(
        {
            "configs_count": validation["configs_count"],
            "unique_configs_count": validation["unique_configs_count"],
            "protocols": validation["protocols"],
            "content_format": validation["format"],
            "validation_errors": validation["errors"],
        }
    )
    nodes = uri_lines(content)[:nodes_per_subscription]
    if not nodes:
        item["status"] = "invalid"
        item["xray_probe"] = {"status": "invalid", "reason": "no_xray_uri_to_probe", "checked_at": utc_timestamp()}
        return item

    attempts = []
    for node in nodes:
        result = await check_xray_uri(node, timeout)
        attempts.append(result.as_dict())
        if result.status == "working":
            item["status"] = "active"
            item["xray_probe"] = {
                "status": "working",
                "checked_at": utc_timestamp(),
                "checked_nodes": len(attempts),
                "result": result.as_dict(),
            }
            return item

    item["status"] = "unverified"
    item["xray_probe"] = {
        "status": "unverified",
        "checked_at": utc_timestamp(),
        "checked_nodes": len(attempts),
        "attempts": attempts,
    }
    return item


async def main_async(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    if not input_path.exists():
        raise SystemExit(f"Input file not found: {input_path}")
    payload = json.loads(input_path.read_text(encoding="utf-8"))
    subscriptions = payload.get("subscriptions", [])
    semaphore = asyncio.Semaphore(max(1, args.concurrency))

    async def guarded(item: dict[str, Any]) -> dict[str, Any]:
        async with semaphore:
            return await probe_item(item, args.timeout, args.nodes_per_subscription)

    payload["subscriptions"] = await asyncio.gather(
        *(guarded(item) for item in subscriptions[: args.max_subscriptions])
    )
    payload["xray_validation"] = {
        "enabled": True,
        "checked_at": utc_timestamp(),
        "max_subscriptions": args.max_subscriptions,
        "nodes_per_subscription": args.nodes_per_subscription,
        "timeout_seconds": args.timeout,
        "policy": "A subscription is active only after at least one supported URI establishes a SOCKS5 CONNECT through Xray.",
    }
    input_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/subscriptions_found.json")
    parser.add_argument("--max-subscriptions", type=int, default=int(os.getenv("MAX_XRAY_SUBSCRIPTION_PROBES", "40")))
    parser.add_argument("--nodes-per-subscription", type=int, default=int(os.getenv("XRAY_NODES_PER_SUBSCRIPTION", "2")))
    parser.add_argument("--timeout", type=float, default=float(os.getenv("XRAY_CHECK_TIMEOUT", "8")))
    parser.add_argument("--concurrency", type=int, default=int(os.getenv("XRAY_CHECK_CONCURRENCY", "4")))
    args = parser.parse_args()
    args.max_subscriptions = max(0, args.max_subscriptions)
    args.nodes_per_subscription = max(1, args.nodes_per_subscription)
    args.timeout = max(2.0, args.timeout)
    args.concurrency = max(1, args.concurrency)
    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()