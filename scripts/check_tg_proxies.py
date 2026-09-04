#!/usr/bin/env python3
"""Run strict Telegram proxy health checks and produce dashboard JSON."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
from pathlib import Path
from typing import Any

from strict_proxy_checker import check_telegram_proxy, check_xray_uri, parse_xray_uri, utc_timestamp
from telegram_mtproto_checker import check_mtproto_proxy_full


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
    enable_xray: bool,
    enable_mtproto: bool,
) -> list[dict[str, Any]]:
    semaphore = asyncio.Semaphore(max(1, concurrency))

    async def check_one(proxy: dict[str, Any]) -> dict[str, Any]:
        normalized = normalize_proxy(proxy)
        async with semaphore:
            # First try standard Telegram proxy check
            result = await check_telegram_proxy(normalized, timeout)
            
            # If Xray is enabled and proxy has a URI, also check through Xray
            xray_result = None
            if enable_xray and normalized.get("url"):
                uri = normalized["url"]
                parsed = parse_xray_uri(uri)
                if parsed:
                    xray_result = await check_xray_uri(uri, timeout)
            
            # If MTProto check is enabled and protocol is mtproto, validate secret
            mtproto_result = None
            if enable_mtproto and normalized.get("protocol") == "mtproto":
                host = normalized.get("host")
                port = normalized.get("port")
                secret = normalized.get("secret")
                
                if host and port and secret:
                    try:
                        mtproto_result = await check_mtproto_proxy_full(
                            host=host,
                            port=int(port),
                            secret=secret,
                            timeout=timeout,
                        )
                    except Exception as exc:
                        mtproto_result = type('obj', (object,), {
                            'status': 'error',
                            'verification': 'mtproto_check',
                            'latency_ms': None,
                            'error': str(exc)[:200],
                        })()
            
            normalized.update(result.as_dict())
            normalized["checked_at"] = utc_timestamp()
            normalized["dns_ok"] = result.verification != "dns"
            normalized["tcp_open"] = result.status in {"working", "unverified"}
            normalized["ping"] = result.latency_ms
            
            # Add Xray verification if available
            if xray_result:
                normalized["xray_verification"] = {
                    "status": xray_result.status,
                    "verification": xray_result.verification,
                    "latency_ms": xray_result.latency_ms,
                    "error": xray_result.error,
                }
                # Upgrade status if Xray confirms working
                if xray_result.status == "working" and result.status == "unverified":
                    normalized["status"] = "working"
                    normalized["verification"] = f"xray_{xray_result.verification}"
            
            # Add MTProto verification if available
            if mtproto_result:
                normalized["mtproto_verification"] = {
                    "status": mtproto_result.status,
                    "verification": mtproto_result.verification,
                    "latency_ms": mtproto_result.latency_ms,
                    "error": mtproto_result.error,
                    "protocol_version": getattr(mtproto_result, 'protocol_version', None),
                }
                # Upgrade status if MTProto check confirms working
                if mtproto_result.status == "working" and result.status == "unverified":
                    normalized["status"] = "working"
                    normalized["verification"] = "mtproto_validated"
            
        return normalized

    return await asyncio.gather(*(check_one(proxy) for proxy in proxies))


def build_payload(
    results: list[dict[str, Any]],
    timeout: float,
    concurrency: int,
    enable_xray: bool,
    enable_mtproto: bool,
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
        "xray_enabled": enable_xray,
        "mtproto_check_enabled": enable_mtproto,
        "verification_policy": {
            "socks5": (
                "SOCKS5 authentication negotiation and CONNECT to a control HTTPS host"
            ),
            "http": "HTTP CONNECT to a control HTTPS host",
            "mtproto": (
                "MTProto secret validation and handshake with protocol negotiation" 
                if enable_mtproto else
                "not marked working by TCP only; requires a Telegram MTProto "
                "client handshake or Xray verification"
            ),
            "xray": "Real connection test through Xray core if URI is available" if enable_xray else "disabled",
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
        default=int(os.getenv("MAX_CHECK_PROXIES", "2000")),
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=float(os.getenv("CHECK_TIMEOUT", "8")),
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=int(os.getenv("CONCURRENCY_LIMIT", "30")),
    )
    parser.add_argument(
        "--enable-xray",
        action="store_true",
        default=os.getenv("ENABLE_XRAY_CHECK", "").lower() in {"1", "true", "yes"},
        help="Enable Xray core verification for proxy URIs",
    )
    parser.add_argument(
        "--enable-mtproto",
        action="store_true",
        default=os.getenv("ENABLE_MTPROTO_CHECK", "true").lower() in {"1", "true", "yes"},
        help="Enable full MTProto secret validation and handshake",
    )
    args = parser.parse_args()

    proxies = load_proxies(Path(args.input))
    proxies.sort(key=lambda item: len(item.get("sources", [])), reverse=True)
    proxies = proxies[: max(0, args.max_check)]

    timeout = max(1.0, args.timeout)
    concurrency = max(1, args.concurrency)
    results = asyncio.run(check_all(proxies, timeout, concurrency, args.enable_xray, args.enable_mtproto))
    payload = build_payload(results, timeout, concurrency, args.enable_xray, args.enable_mtproto)

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
    if args.enable_xray:
        xray_verified = sum(1 for p in results if p.get("xray_verification"))
        print(f"Xray verified: {xray_verified}")
    if args.enable_mtproto:
        mtproto_verified = sum(1 for p in results if p.get("mtproto_verification", {}).get("status") == "working")
        print(f"MTProto verified: {mtproto_verified}")


if __name__ == "__main__":
    main()