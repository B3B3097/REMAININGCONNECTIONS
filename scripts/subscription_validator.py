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


def _try_clash_yaml(text: str) -> tuple[list[str], dict[str, int]] | None:
    """Parse Clash YAML format and extract unique proxies."""
    try:
        data = yaml.safe_load(text)
        if not isinstance(data, dict):
            return None
        
        proxies = data.get("proxies", [])
        if not isinstance(proxies, list):
            return None
        
        seen_uris = set()
        protocols = {}
        
        for item in proxies:
            if not isinstance(item, dict):
                continue
            
            proxy_type = item.get("type", "").lower()
            server = item.get("server")
            port = item.get("port")
            
            if not server or not port:
                continue
            
            # Create unique key for deduplication
            unique_key = f"{proxy_type}://{server}:{port}"
            
            if unique_key not in seen_uris:
                seen_uris.add(unique_key)
                protocols[proxy_type] = protocols.get(proxy_type, 0) + 1
        
        return list(seen_uris), protocols if seen_uris else None
    except (yaml.YAMLError, AttributeError, KeyError):
        return None


def _try_xray_json(text: str) -> tuple[list[str], dict[str, int]] | None:
    """Parse Xray JSON format and extract unique proxies."""
    try:
        data = json.loads(text)
        if not isinstance(data, dict):
            return None
        
        outbounds = data.get("outbounds", [])
        if not isinstance(outbounds, list):
            return None
        
        seen_uris = set()
        protocols = {}
        
        for item in outbounds:
            if not isinstance(item, dict):
                continue
            
            protocol = item.get("protocol", "").lower()
            settings = item.get("settings", {})
            
            if not isinstance(settings, dict):
                continue
            
            servers = settings.get("servers", [])
            if isinstance(servers, list):
                for srv in servers:
                    if not isinstance(srv, dict):
                        continue
                    
                    address = srv.get("address")
                    port = srv.get("port")
                    
                    if address and port:
                        unique_key = f"{protocol}://{address}:{port}"
                        if unique_key not in seen_uris:
                            seen_uris.add(unique_key)
                            protocols[protocol] = protocols.get(protocol, 0) + 1
        
        return list(seen_uris), protocols if seen_uris else None
    except (json.JSONDecodeError, AttributeError, KeyError):
        return None


def validate_subscription(content: str) -> dict[str, Any]:
    """
    Validate subscription content and return analysis.
    Returns unique node count and protocol distribution.
    """
    if not content or len(content) > MAX_TEXT_BYTES:
        return {
            "valid": False,
            "format": "invalid",
            "total_nodes": 0,
            "protocols": {},
            "reason": "empty or too large",
        }

    # Try base64 decode first
    decoded = _decode_base64_subscription(content)
    if decoded:
        content = decoded

    # Try URI list format
    uris, protocols = _collect_uri_lines(content)
    if uris:
        return {
            "valid": True,
            "format": "uri_list",
            "total_nodes": len(uris),
            "protocols": protocols,
        }

    # Try Clash YAML
    result = _try_clash_yaml(content)
    if result:
        uris, protocols = result
        return {
            "valid": True,
            "format": "clash_yaml",
            "total_nodes": len(uris),
            "protocols": protocols,
        }

    # Try Xray JSON
    result = _try_xray_json(content)
    if result:
        uris, protocols = result
        return {
            "valid": True,
            "format": "xray_json",
            "total_nodes": len(uris),
            "protocols": protocols,
        }

    return {
        "valid": False,
        "format": "unknown",
        "total_nodes": 0,
        "protocols": {},
        "reason": "unrecognized format",
    }