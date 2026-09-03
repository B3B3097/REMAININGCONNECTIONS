#!/usr/bin/env python3
"""Content validation for public proxy subscription files."""

from __future__ import annotations

import base64
import json
import re
from collections import Counter
from typing import Any
from urllib.parse import urlparse

import yaml

URI_PROTOCOLS = {
    "vless",
    "vmess",
    "ss",
    "ssr",
    "trojan",
    "trojan-go",
    "hysteria",
    "hysteria2",
    "hy2",
    "tuic",
    "wireguard",
    "wg",
    "socks",
    "socks5",
    "http",
    "https",
}
URI_RE = re.compile(
    r"(?im)^\s*((?:" + "|".join(re.escape(item) for item in URI_PROTOCOLS) + r")://[^\s#]+(?:#[^\r\n]*)?)\s*$"
)
BASE64_CANDIDATE_RE = re.compile(r"^[A-Za-z0-9+/_=\-\s]{32,}$")
MAX_TEXT_BYTES = 10_000_000  # Увеличен до 10 МБ


def _decode_base64_subscription(text: str) -> str | None:
    compact = "".join(text.split())
    if not compact or len(compact) > MAX_TEXT_BYTES or not BASE64_CANDIDATE_RE.fullmatch(text):
        return None
    try:
        compact += "=" * (-len(compact) % 4)
        decoded = base64.urlsafe_b64decode(compact.encode("ascii"))
        if not decoded or len(decoded) > MAX_TEXT_BYTES:
            return None
        value = decoded.decode("utf-8-sig")
        return value if "://" in value else None
    except (ValueError, UnicodeDecodeError):
        return None


def _valid_uri(value: str) -> tuple[str, str] | None:
    value = value.strip()
    try:
        parsed = urlparse(value)
    except ValueError:
        return None
    protocol = parsed.scheme.lower()
    if protocol not in URI_PROTOCOLS:
        return None
    if protocol == "vmess":
        return protocol, value
    if not parsed.hostname and protocol not in {"wireguard", "wg"}:
        return None
    try:
        if parsed.port is not None and not 1 <= parsed.port <= 65535:
            return None
    except ValueError:
        return None
    return protocol, value


def _collect_uri_lines(text: str) -> tuple[list[str], Counter[str]]:
    values: list[str] = []
    protocols: Counter[str] = Counter()
    for match in URI_RE.finditer(text):
        candidate = match.group(1)
        parsed = _valid_uri(candidate)
        if parsed is None:
            continue
        protocol, normalized = parsed
        values.append(normalized)
        protocols[protocol] += 1
    return values, protocols


def _walk_structured_config(value: Any, protocols: Counter[str]) -> int:
    if isinstance(value, list):
        return sum(_walk_structured_config(item, protocols) for item in value)
    if not isinstance(value, dict):
        return 0

    kind = str(value.get("type") or value.get("protocol") or "").lower()
    host = value.get("server") or value.get("address") or value.get("hostname")
    port = value.get("port")
    if kind in URI_PROTOCOLS and host:
        try:
            if port is None or 1 <= int(port) <= 65535:
                protocols[kind] += 1
                return 1
        except (TypeError, ValueError):
            pass

    total = 0
    for key, child in value.items():
        if key in {"proxies", "outbounds", "nodes", "servers"}:
            total += _walk_structured_config(child, protocols)
    return total


def validate_subscription_content(text: str, path: str = "") -> dict[str, Any]:
    """Return deterministic parse diagnostics without treating arbitrary text as nodes."""
    if not isinstance(text, str) or not text.strip():
        return {
            "valid": False,
            "format": "empty",
            "configs_count": 0,
            "unique_configs_count": 0,
            "protocols": {},
            "errors": ["empty_content"],
        }

    raw = text[:MAX_TEXT_BYTES]
    decoded = _decode_base64_subscription(raw)
    effective = decoded or raw
    uri_values, protocols = _collect_uri_lines(effective)
    unique_uris = set(uri_values)
    structured_count = 0
    detected_format = "base64_uri_list" if decoded else "uri_list"
    errors: list[str] = []

    lower_path = path.lower()
    is_structured = lower_path.endswith((".yaml", ".yml", ".json")) or effective.lstrip().startswith(("{", "[", "proxies:"))
    if is_structured:
        try:
            parsed: Any
            if lower_path.endswith(".json") or effective.lstrip().startswith(("{", "[")):
                parsed = json.loads(effective)
                detected_format = "json"
            else:
                parsed = yaml.safe_load(effective)
                detected_format = "yaml"
            structured_count = _walk_structured_config(parsed, protocols)
        except (json.JSONDecodeError, yaml.YAMLError, TypeError, ValueError) as exc:
            errors.append(f"structured_parse_error:{type(exc).__name__}")

    total = len(unique_uris) + structured_count
    if total == 0 and not errors:
        errors.append("no_supported_configs")
    return {
        "valid": total > 0,
        "format": detected_format,
        "configs_count": total,
        "unique_configs_count": len(unique_uris),
        "protocols": dict(sorted(protocols.items())),
        "errors": errors,
    }