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
            
            # Determine status and bypass status
            status = "failed"
            bypass_status = None
            
            if result.get("tcp_ok") or result.get("socket_connected"):
                # Basic connectivity works
                if result.get("telegram_handshake_ok"):
                    status = "working"
                else:
                    # TCP works but handshake fails - might need bypass
                    status = "failed"
                    bypass_status = "might_work_with_bypass"
            
            # If Xray is enabled and proxy has a URI, also check through Xray
            if enable_xray and normalized.get("url"):
                parsed = parse_xray_uri(normalized["url"])
                if parsed:
                    xray_result = await check_xray_uri(normalized["url"], timeout)
                    result.update(xray_result)
                    if xray_result.get("xray_ok"):
                        # Xray works - this means it works with bypass
                        if status == "failed":
                            status = "working"
                            bypass_status = "works_with_bypass"

            # If MTProto is enabled, run full MTProto check
            if enable_mtproto and normalized.get("protocol") == "mtproto":
                mtproto_result = await check_mtproto_proxy_full(
                    normalized.get("host"),
                    normalized.get("port"),
                    normalized.get("secret"),
                    timeout,
                )
                result.update(mtproto_result)
                if mtproto_result.get("mtproto_handshake_valid"):
                    status = "working"
                    # If it only works via MTProto but not basic check, mark as bypass
                    if not result.get("telegram_handshake_ok"):
                        bypass_status = "works_with_bypass"

            result.update({
                "status": status,
                "bypass_status": bypass_status,
                "working": status == "working",  # Keep for backward compatibility
                "checked_at": utc_timestamp(),
            })
            return result

    tasks = [check_one(p) for p in proxies]
    return await asyncio.gather(*tasks)


def merge_results(
    existing: list[dict[str, Any]],
    checked: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    by_key = {}
    for p in existing:
        key = (p.get("host") or p.get("server"), p.get("port"))
        by_key[key] = p

    for checked_proxy in checked:
        key = (
            checked_proxy.get("host") or checked_proxy.get("server"),
            checked_proxy.get("port"),
        )
        if key in by_key:
            by_key[key].update(checked_proxy)
        else:
            by_key[key] = checked_proxy

    return list(by_key.values())


async def main_async(args: argparse.Namespace) -> None:
    input_path = Path(args.input)
    output_path = Path(args.output)
    final_output_path = Path(args.final_output)

    existing_proxies = load_proxies(input_path)
    if not existing_proxies:
        print("[!] No proxies to check.")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps({"proxies": [], "generated_at": utc_timestamp()}, indent=2),
            encoding="utf-8",
        )
        if final_output_path:
            final_output_path.parent.mkdir(parents=True, exist_ok=True)
            final_output_path.write_text(
                json.dumps({"proxies": [], "generated_at": utc_timestamp()}, indent=2),
                encoding="utf-8",
            )
        return

    max_check = args.max_check
    to_check = existing_proxies[:max_check] if max_check > 0 else existing_proxies

    print(f"[*] Checking {len(to_check)} proxies (timeout={args.timeout}s, concurrency={args.concurrency})...")
    checked = await check_all(
        to_check,
        args.timeout,
        args.concurrency,
        args.enable_xray,
        args.enable_mtproto,
    )

    merged = merge_results(existing_proxies, checked)
    working = [p for p in merged if p.get("status") == "working"]
    
    print(f"[+] Checked {len(checked)} proxies. {len(working)} working.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(
            {"proxies": merged, "generated_at": utc_timestamp()},
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    print(f"[+] Wrote {output_path}")

    if final_output_path:
        final_output_path.parent.mkdir(parents=True, exist_ok=True)
        final_output_path.write_text(
            json.dumps(
                {"proxies": merged, "generated_at": utc_timestamp()},
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        print(f"[+] Wrote {final_output_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Check Telegram proxies with strict validation")
    parser.add_argument("--input", default="extracted/tg_proxies_extracted.json")
    parser.add_argument("--output", default="checked/tg_proxies_checked.json")
    parser.add_argument("--final-output", default="data/tg_proxies_found.json")
    parser.add_argument("--max-check", type=int, default=2000)
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--concurrency", type=int, default=30)
    parser.add_argument("--enable-xray", action="store_true", default=False)
    parser.add_argument("--enable-mtproto", action="store_true", default=False)
    args = parser.parse_args()

    asyncio.run(main_async(args))


if __name__ == "__main__":
    main()