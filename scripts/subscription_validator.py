#!/usr/bin/env python3
"""Content validation for public proxy subscription files."""

from __future__ import annotations

import base64
import json
import re
from typing import Any
from urllib.parse import urlparse

import yaml

URI_PROTOCOLS = {
    "vless",
    "vmess",
    "ss",
    "shadowsocks",
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
MAX_TEXT_BYTES = 10_000_000


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


def _collect_uri_lines(text: str) -> tuple[list[str], dict[str, int]]:
    """Collect unique proxy URIs and count by protocol."""
    seen_uris = set()
    protocols = {}

    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        result = _valid_uri(line)
        if result:
            protocol, uri = result
            if uri not in seen_uris:
                seen_uris.add(uri)
                protocols[protocol] = protocols.get(protocol, 0) + 1

    return list(seen_uris), protocols


def _iter_outbound_endpoints(item: Any) -> list[tuple[str, str, Any]]:
    """Extract (protocol, host, port) endpoints from one structured entry.

    Supports Clash entries (type/server/port), sing-box entries
    (type/server/server_port) and V2Ray outbounds (protocol + settings).
    """
    endpoints: list[tuple[str, str, Any]] = []
    if not isinstance(item, dict):
        return endpoints

    # Clash / sing-box style flat entry
    entry_type = item.get("type")
    if isinstance(entry_type, str) and entry_type:
        server = item.get("server")
        port = item.get("port", item.get("server_port"))
        if server and port:
            endpoints.append((entry_type.lower(), str(server), port))

    # V2Ray style outbound with nested servers
    protocol = item.get("protocol")
    if isinstance(protocol, str) and protocol:
        settings = item.get("settings")
        if isinstance(settings, dict):
            for group in ("vnext", "servers"):
                servers = settings.get(group)
                if not isinstance(servers, list):
                    continue
                for srv in servers:
                    if isinstance(srv, dict) and srv.get("address") and srv.get("port"):
                        endpoints.append((protocol.lower(), str(srv["address"]), srv["port"]))

    return endpoints


def _extract_structured_configs(data: Any) -> tuple[list[str], dict[str, int]] | None:
    """Extract unique proxy endpoints from parsed Clash/V2Ray/sing-box structures.

    Dedup key is "type://host:port"; returns None when no configs are found.
    """
    if isinstance(data, dict):
        entries: list[Any] = []
        proxies = data.get("proxies")
        if isinstance(proxies, list):
            entries.extend(proxies)
        outbounds = data.get("outbounds")
        if isinstance(outbounds, list):
            entries.extend(outbounds)
    elif isinstance(data, list):
        entries = list(data)
    else:
        return None

    seen: set[str] = set()
    protocols: dict[str, int] = {}
    for item in entries:
        for protocol, host, port in _iter_outbound_endpoints(item):
            unique_key = f"{protocol}://{host}:{port}"
            if unique_key not in seen:
                seen.add(unique_key)
                protocols[protocol] = protocols.get(protocol, 0) + 1

    return (list(seen), protocols) if seen else None


def _content_success(format_name: str, configs: list[str], protocols: dict[str, int]) -> dict[str, Any]:
    count = len(configs)
    return {
        "valid": True,
        "format": format_name,
        "configs_count": count,
        "unique_configs_count": count,
        "protocols": protocols,
        "errors": [],
        "warnings": [],
        "total_nodes": count,
    }


def _content_failure(format_name: str, errors: list[str]) -> dict[str, Any]:
    return {
        "valid": False,
        "format": format_name,
        "configs_count": 0,
        "unique_configs_count": 0,
        "protocols": {},
        "errors": errors,
        "warnings": [],
        "total_nodes": 0,
    }


def _first_line(value: str) -> str:
    lines = value.strip().splitlines()
    return lines[0].strip() if lines else "unknown error"


def validate_subscription_content(content: str, filename: str | None = None) -> dict[str, Any]:
    """
    Validate subscription content and return a detailed analysis.

    Recognized formats: plain URI lists, base64-encoded URI lists and
    structured Clash/V2Ray/sing-box configs in YAML or JSON.
    """
    if not content or not content.strip():
        return _content_failure("empty", ["empty_content"])

    # (1) Plain URI list
    uris, protocols = _collect_uri_lines(content)
    if uris:
        return _content_success("uri_list", uris, protocols)

    # (2) Base64-encoded URI list
    if BASE64_CANDIDATE_RE.fullmatch(content):
        decoded = _decode_base64_subscription(content)
        if decoded:
            uris, protocols = _collect_uri_lines(decoded)
            if uris:
                return _content_success("base64_uri_list", uris, protocols)

    stripped = content.lstrip()

    # (3) YAML (Clash / V2Ray)
    looks_yaml = bool(filename) and filename.lower().endswith((".yaml", ".yml"))
    if looks_yaml or stripped.startswith(("proxies:", "outbounds:")):
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as exc:
            return _content_failure("yaml", [f"yaml_parse_error: {_first_line(str(exc))}"])
        result = _extract_structured_configs(data)
        if result:
            configs, protocols = result
            return _content_success("yaml", configs, protocols)

    # (4) JSON (Xray / V2Ray / sing-box)
    looks_json = bool(filename) and filename.lower().endswith(".json")
    if looks_json or stripped.startswith(("{", "[")):
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            return _content_failure("json", [f"json_parse_error: {_first_line(str(exc))}"])
        result = _extract_structured_configs(data)
        if result:
            configs, protocols = result
            return _content_success("json", configs, protocols)

    # (5) Unrecognized
    return _content_failure("unknown", ["unrecognized_format"])


def validate_subscription(content: str) -> dict[str, Any]:
    """
    Validate subscription content and return analysis.
    Returns unique node count and protocol distribution.

    Kept for backward compatibility: a thin wrapper around
    validate_subscription_content() exposing the legacy response schema.
    """
    if not content or len(content) > MAX_TEXT_BYTES:
        return {
            "valid": False,
            "format": "invalid",
            "total_nodes": 0,
            "protocols": {},
            "reason": "empty or too large",
        }

    result = validate_subscription_content(content)
    response: dict[str, Any] = {
        "valid": result["valid"],
        "format": result["format"],
        "total_nodes": result["total_nodes"],
        "protocols": result["protocols"],
    }
    if not result["valid"]:
        response["reason"] = "; ".join(result["errors"]) or "unrecognized format"
    return response
