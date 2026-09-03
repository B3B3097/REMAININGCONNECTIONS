#!/usr/bin/env python3
"""Run strict Telegram proxy health checks and produce dashboard JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from strict_proxy_checker import check_telegram_proxy, utc_timestamp


def load_proxies(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
        values = payload.get("proxies", [])
        return values if isinstance(values, list) else []
    except (OSError, json.JSONDecodeError):
        return []


def normalize_proxy(proxy: dict[str, Any]) -> dict[str, Any]:
    protocol = str(proxy.get("protocol") or "mtproto").lower()
    if protocol in {"socks", "socks5"}:
        protocol = "socks5"
    elif protocol in {"http", "https"}:
        protocol = "http"

    host = proxy.get("host") or proxy.get("server")
    return {
        "host": host,
        "server": host,
        "port": proxy.get("port"),
        "secret": proxy.get("secret"),
        "protocol": protocol,
        "tg_url": proxy.get("tg_url"),
        "tme_url": proxy.get("tme_url"),
        "url": proxy.get("url"),
        "sources": proxy.get("sources", []),
    }


async def check_all(
    proxies: list[dict[str, Any]],
    timeout: float,
    concurrency: int,
) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def check_one(proxy: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_proxy(proxy)
        async with semaphore:
            result = await check_telegram_proxy(normalized, timeout)
        normalized.update(result.as_dict())
        normalized["checked_at"] = utc_timestamp()
        normalized["dns_ok"] = result.verification != "dns"
        normalized["tcp_open"] = result.status in {"working", "unverified"}
        normalized["ping"] = result.latency_ms
        return normalized

    return await asyncio.gather(*(check_one(proxy) for proxy in proxies))


def build_payload(
    results: list[dict[str, Any]],
    timeout: float,
    concurrency: int,
) -> dict[str, Any]:
    working = [item for item in results if item["status"] == "working"]
    unverified = [item for item in results if item["status"] == "unverified"]
    failed = [item for item in results if item["status"] not in {"working", "unverified"}]
    latencies = [
        item["latency_ms"]
        for item in working
        if item.get("latency_ms") is not None
    ]

    results.sort(
        key=lambda item: (
            item["status"] != "working",
            item["status"] != "unverified",
            item["latency_ms"]
            if item.get("latency_ms") is not None
            else float("inf"),
            -len(item.get("sources", [])),
        )
    )
    for index, item in enumerate(results, start=1):
        item["id"] = index

    return {
        "generated_at": utc_timestamp(),
        "generator": "scripts/check_tg_proxies.py",
        "telegram_channel": "https://t.me/REMAININGCONNECTIONS",
        "checked_count": len(results),
        "working_count": len(working),
        "unverified_count": len(unverified),
        "offline_count": len(failed),
        "online_count": len(working),
        "dns_fail_count": sum(
            1 for item in results if item.get("verification") == "dns"
        ),
        "avg_latency_ms": (
            round(sum(latencies) / len(latencies), 2) if latencies else None
        ),
        "check_timeout_seconds": timeout,
        "concurrency_limit": concurrency,
        "verification_policy": {
            "socks5": (
                "SOCKS5 authentication negotiation and CONNECT to a control HTTPS host"
            ),
            "http": "HTTP CONNECT to a control HTTPS host",
            "mtproto": (
                "not marked working by TCP only; requires a Telegram MTProto "
                "client handshake"
            ),
        },
        "proxies": results,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="extracted/tg_proxies_extracted.json")
    parser.add_argument("--output", default="checked/tg_proxies_checked.json")
    parser.add_argument(
        "--final-output",
        default=os.getenv("OUTPUT_FILE", "data/tg_proxies_found.json"),
    )
    parser.add_argument(
        "--max-check",
        type=int,
        default=int(os.getenv("MAX_CHECK_PROXIES", "500")),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("CHECK_TIMEOUT", "6")),
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.getenv("CONCURRENCY_LIMIT", "20")),
    )
    args = parser.parse_args()

    proxies = load_proxies(Path(args.input))
    proxies.sort(key=lambda item: len(item.get("sources", [])), reverse=True)
    proxies = proxies[: max(0, args.max_check)]

    timeout = max(1.0, args.timeout)
    concurrency = max(1, args.concurrency)
    results = asyncio.run(check_all(proxies, timeout, concurrency))
    payload = build_payload(results, timeout, concurrency)

    for output in (Path(args.output), Path(args.final_output)):
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    print(f"Checked: {payload['checked_count']}")
    print(f"Working: {payload['working_count']}")
    print(f"Unverified MTProto: {payload['unverified_count']}")
    print(f"Failed: {payload['offline_count']}")


if __name__ == "__main__":
    main()