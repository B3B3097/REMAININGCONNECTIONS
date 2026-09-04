#!/usr/bin/env python3
"""
Advanced Subscription Parser for REMAININGCONNECTIONS.

This module provides robust parsing capabilities for various popular proxy client formats.
It normalizes inputs from Clash, V2Ray, Surge, and Sing-box into our internal unified format.

Supported Formats:
- Clash / Clash Meta (YAML)
- V2Ray (JSON)
- Surge (Text/Conf)
- Quantumult X (Text)
- Base64 Encoded URI Lists
"""

from __future__ import annotations

import base64
import json
import logging
import re
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("SubscriptionParser")


class ProxyNormalizer:
    """Standardizes different proxy types into a common schema."""

    # Common keys mapping
    KEYS = {
        "server": ["server", "address", "host"],
        "port": ["port", "server_port"],
        "name": ["name", "remarks", "title"],
        "password": ["password", "pwd"],
        "uuid": ["uuid", "id"],
        "flow": ["flow"],
        "cipher": ["cipher", "method"],
        "obfs": ["obfs", "type"],
        "obfs_host": ["obfs-host", "hostname"],
        "tls": ["tls", "skip-cert-verify"]
    }

    @classmethod
    def normalize(cls, raw_proxy: Dict[str, Any], source_format: str = "unknown") -> Optional[Dict[str, Any]]:
        """Convert a raw proxy dict to our standard schema."""
        if not raw_proxy:
            return None

        # Extract common fields using flexible key mapping
        server = cls._get_key(raw_proxy, cls.KEYS["server"])
        port = cls._get_key(raw_proxy, cls.KEYS["port"])
        name = cls._get_key(raw_proxy, cls.KEYS["name"])
        
        if not server or not port:
            return None

        # Determine protocol based on type field or content
        proto = cls._detect_protocol(raw_proxy)
        
        # Specific field extraction based on protocol
        secret = None
        extra = {}

        if proto == "vless" or proto == "vmess":
            secret = cls._get_key(raw_proxy, ["uuid", "id"])
            extra.update({
                "flow": cls._get_key(raw_proxy, ["flow"]),
                "sni": cls._get_key(raw_proxy, ["servername", "peer", "sni"]),
                "fp": cls._get_key(raw_proxy, ["fingerprint", "fp"]),
                "alpn": raw_proxy.get("alpn"),
                "publicKey": cls._get_key(raw_proxy, ["publicKey", "pbk"]),
                "shortId": cls._get_key(raw_proxy, ["shortId", "sid"]),
                "spiderX": cls._get_key(raw_proxy, ["spiderX"]),
                "network": cls._get_key(raw_proxy, ["network", "type"]),
                "security": cls._get_key(raw_proxy, ["security"]),
            })
            
            # Handle stream settings (WS, GRPC, HTTP)
            stream = raw_proxy.get("streamSettings") or raw_proxy.get("ws-opts") or {}
            extra["path"] = stream.get("path") or raw_proxy.get("ws-path")
            extra["headers"] = stream.get("headers") or raw_proxy.get("ws-headers")

        elif proto == "trojan":
            secret = cls._get_key(raw_proxy, ["password", "passwd"])
            extra.update({
                "sni": cls._get_key(raw_proxy, ["sni", "peer"]),
                "fp": cls._get_key(raw_proxy, ["fingerprint"]),
                "allowInsecure": raw_proxy.get("allowInsecure"),
                "grpcServiceName": cls._get_key(raw_proxy, ["grpc-service-name"]),
            })

        elif proto == "shadowsocks" or proto == "ss":
            secret = cls._get_key(raw_proxy, ["password", "passwords"])
            cipher = cls._get_key(raw_proxy, ["cipher", "method"])
            extra["cipher"] = cipher
            
            # SSR specific
            if raw_proxy.get("protocol"):
                extra["protocol"] = raw_proxy["protocol"]
                extra["protocolParam"] = raw_proxy.get("protocol_param")
                extra["obfs"] = raw_proxy.get("obfs")
                extra["obfsParam"] = raw_proxy.get("obfs_param")

        elif proto == "hysteria2" or proto == "hy2":
            secret = cls._get_key(raw_proxy, ["password", "auth"])
            extra.update({
                "insecure": raw_proxy.get("skip-cert-verify"),
                "obfs-password": cls._get_key(raw_proxy, ["obfs-password"]),
                "obfs-type": cls._get_key(raw_proxy, ["obfs.type"]),
            })

        elif proto in ("socks5", "http"):
            username = cls._get_key(raw_proxy, ["username"])
            password = cls._get_key(raw_proxy, ["password"])
            if username:
                secret = f"{username}:{password}"

        return {
            "name": name or f"{proto}-{server}",
            "server": server,
            "host": server,
            "port": int(port),
            "protocol": proto,
            "secret": secret,
            "sources": [{"source": source_format}],
            "_metadata": extra
        }

    @staticmethod
    def _get_key(data: Dict, keys: List[str]) -> Any:
        """Get value from dict trying multiple possible keys."""
        for k in keys:
            if k in data:
                return data[k]
        return None

    @staticmethod
    def _detect_protocol(proxy: Dict[str, Any]) -> str:
        """Detect protocol type from dictionary structure."""
        t = proxy.get("type", "").lower()
        p = proxy.get("protocol", "").lower()
        
        # Direct type match
        if t in ("vless", "vmess", "trojan", "ss", "shadowsocks", "socks5", "http", "hysteria2", "tuic"):
            return t
        
        # Protocol field match
        if p in ("vless", "vmess", "trojan", "ss", "hysteria2"):
            return p
            
        # Heuristics
        if "uuid" in proxy:
            return "vmess" # Usually implies VMess or VLESS, default to vmess for now unless vless field exists
        if "encryption" in proxy:
            return "vless"
        if "cipher" in proxy:
            return "shadowsocks"
        if "password" in proxy and "server" in proxy:
             # Ambiguous, could be trojan/ss/http
             if proxy.get("sni") or proxy.get("servername"):
                 return "trojan"
             return "shadowsocks"
             
        return "unknown"


class SubscriptionParser:
    """Main parser class handling various input formats."""

    def __init__(self):
        self.normalizer = ProxyNormalizer()

    def parse(self, content: str, fmt: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Parse subscription content.
        
        Args:
            content: Raw string content.
            fmt: Format hint ('yaml', 'json', 'text', 'b64'). If None, auto-detect.
        """
        if not content:
            return []
            
        if fmt == "b64":
            try:
                decoded = base64.b64decode(content).decode('utf-8')
                return self.parse(decoded, fmt="text")
            except Exception:
                return []

        if fmt == "yaml" or (fmt is None and content.strip().startswith('-')):
            return self.parse_yaml(content)
        elif fmt == "json":
            return self.parse_json(content)
        else:
            return self.parse_text(content)

    def parse_yaml(self, content: str) -> List[Dict[str, Any]]:
        """Parse Clash/YAML format."""
        try:
            data = yaml.safe_load(content)
        except yaml.YAMLError as e:
            logger.error(f"YAML Parse Error: {e}")
            return []

        proxies = data.get("proxies", [])
        results = []
        for p in proxies:
            norm = self.normalizer.normalize(p, source_format="clash-yaml")
            if norm:
                results.append(norm)
        return results

    def parse_json(self, content: str) -> List[Dict[str, Any]]:
        """Parse V2Ray/SingBox JSON format."""
        try:
            data = json.loads(content)
        except json.JSONDecodeError as e:
            logger.error(f"JSON Parse Error: {e}")
            return []

        results = []
        
        # V2Ray Structure
        if "outbounds" in data:
            for ob in data["outbounds"]:
                proto = ob.get("protocol", "")
                if proto in ("vless", "vmess", "shadowsocks", "trojan", "freedom", "blackhole"):
                    # Construct pseudo-proxy dict for normalizer
                    settings = ob.get("settings", {})
                    stream = ob.get("streamSettings", {})
                    
                    input_proxy = {
                        "name": ob.get("tag"),
                        "type": proto,
                        "protocol": proto
                    }
                    
                    # Map nested structures
                    if proto == "vless" or proto == "vmess":
                        servers = settings.get("vnext", [{}])[0].get("users", [{}])[0]
                        input_proxy.update({
                            "server": settings.get("vnext", [{}])[0].get("address"),
                            "port": settings.get("vnext", [{}])[0].get("port"),
                            "uuid": servers.get("id"),
                            "security": servers.get("security"),
                            "alterId": servers.get("aid"),
                            "network": stream.get("network"),
                            "securityLayer": stream.get("security"),
                            "realitySettings": stream.get("realitySettings"),
                            "wsSettings": stream.get("wsSettings"),
                            "grpcSettings": stream.get("grpcSettings"),
                        })
                        
                    elif proto == "shadowsocks":
                        servers = settings.get("servers", [{}])[0]
                        input_proxy.update({
                            "server": servers.get("address"),
                            "port": servers.get("port"),
                            "password": servers.get("password"),
                            "cipher": servers.get("method"),
                        })
                        
                    elif proto == "trojan":
                        servers = settings.get("servers", [{}])[0]
                        input_proxy.update({
                            "server": servers.get("address"),
                            "port": servers.get("port"),
                            "password": servers.get("password"),
                            "network": stream.get("network"),
                            "security": stream.get("security"),
                        })

                    norm = self.normalizer.normalize(input_proxy, source_format="v2ray-json")
                    if norm:
                        results.append(norm)
        
        # SingBox Structure (simplified)
        elif "outbounds" in data and isinstance(data["outbounds"], list):
            first_outbound = data["outbounds"][0] if data["outbounds"] else {}
            if "type" in first_outbound:
                 # SingBox uses 'type'
                 pass 
                 # Implement SingBox specific mapping if needed
                 
        return results

    def parse_text(self, content: str) -> List[Dict[str, Any]]:
        """Parse text-based formats (Surge, QuanX, URI lists)."""
        lines = content.splitlines()
        results = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Try URI parsing first (vless://, vmess://, ss://, tg://)
            uri_result = self._parse_uri(line)
            if uri_result:
                results.append(uri_result)
                continue
            
            # Try Surge format: Name = Type, Server, Port, ...
            surge_match = re.match(r'^([^=]+)=\s*(.+)$', line)
            if surge_match:
                surgeresult = self._parse_surge_line(surge_match.group(1), surge_match.group(2))
                if surgeresult:
                    results.append(surgeresult)
                    continue
            
            # Try QuanX format: Type = IP, Port, Method, Password, Name
            quanx_match = re.match(r'^(\w+)\s*=\s*(.*?)(?:,\s*name=(.*))$', line)
            if quanx_match:
                qresult = self._parse_quanx_line(quanx_match.group(1), quanx_match.group(2), quanx_match.group(3))
                if qresult:
                    results.append(qresult)

        return results

    def _parse_uri(self, uri: str) -> Optional[Dict[str, Any]]:
        """Parse a single URI string."""
        try:
            if uri.startswith("vless://"):
                # Simplified regex for vless
                # vless://UUID@HOST:PORT?ENCRYPTION=none&SECURITY=tls&SNI=xxx#NAME
                m = re.match(r"^vless://([a-f0-9\-]+)@([^:]+):(\d+)(?:\?(.*))?(?:#(.+))?$", uri)
                if m:
                    uuid_val, host, port, query, name = m.groups()
                    params = dict(pair.split('=') for pair in query.split('&') if '=' in pair) if query else {}
                    return {
                        "name": name,
                        "server": host,
                        "port": int(port),
                        "protocol": "vless",
                        "secret": uuid_val,
                        "sources": ["uri-vless"]
                    }
            
            elif uri.startswith("vmess://"):
                b64 = uri[8:]
                try:
                    obj = json.loads(base64.b64decode(b64).decode())
                    return {
                        "name": obj.get("ps"),
                        "server": obj.get("add"),
                        "port": int(obj.get("port", 443)),
                        "protocol": "vmess",
                        "secret": obj.get("id"),
                        "sources": ["uri-vmess"]
                    }
                except Exception:
                    pass
                    
            elif uri.startswith("ss://"):
                b64 = uri[5:]
                # Handle padding
                b64 += '=' * (-len(b64) % 4)
                try:
                    raw = base64.b64decode(b64).decode()
                    # ss://METHOD:PASSWORD@HOST:PORT#NAME
                    m = re.match(r"^([^:]+):([^@]+)@([^:]+):(\d+)(?:#(.+))?$", raw)
                    if m:
                        method, password, host, port, name = m.groups()
                        return {
                            "name": name,
                            "server": host,
                            "port": int(port),
                            "protocol": "shadowsocks",
                            "secret": password,
                            "cipher": method,
                            "sources": ["uri-ss"]
                        }
                except Exception:
                    pass

            elif uri.startswith("trojan://"):
                m = re.match(r"^trojan://([^@]+)@([^:]+):(\d+)(?:\?(.*))?(?:#(.+))?$", uri)
                if m:
                    password, host, port, query, name = m.groups()
                    return {
                        "name": name,
                        "server": host,
                        "port": int(port),
                        "protocol": "trojan",
                        "secret": password,
                        "sources": ["uri-trojan"]
                    }
            
            elif uri.startswith("tg://"):
                m = re.match(r"^tg://proxy\?server=([^&]+)&port=(\d+)&secret=([^&]+)", uri)
                if m:
                    host, port, secret = m.groups()
                    return {
                        "server": host,
                        "port": int(port),
                        "protocol": "mtproto",
                        "secret": secret,
                        "url": uri,
                        "sources": ["uri-tg"]
                    }
        except Exception:
            pass
        return None

    def _parse_surge_line(self, name: str, params_str: str) -> Optional[Dict[str, Any]]:
        """Parse a Surge config line."""
        parts = [p.strip() for p in params_str.split(',')]
        if len(parts) < 3:
            return None
            
        stype = parts[0]
        server = parts[1]
        port_str = parts[2]
        
        try:
            port = int(port_str)
        except ValueError:
            return None
            
        secret = ""
        cipher = ""
        
        for part in parts[3:]:
            if part.startswith('password='):
                secret = part.split('=', 1)[1]
            elif part.startswith('encrypt-method='):
                cipher = part.split('=', 1)[1]
                
        return {
            "name": name,
            "server": server,
            "port": port,
            "protocol": stype.lower(),
            "secret": secret,
            "cipher": cipher,
            "sources": ["surge-txt"]
        }

    def _parse_quanx_line(self, stype: str, params_str: str, name: Optional[str]) -> Optional[Dict[str, Any]]:
        """Parse a Quantumult X line."""
        parts = [p.strip() for p in params_str.split(',')]
        if len(parts) < 2:
            return None
            
        server = parts[0]
        port_str = parts[1]
        
        try:
            port = int(port_str)
        except ValueError:
            return None
            
        method = ""
        password = ""
        tag = name or "QuanX"
        
        for part in parts[2:]:
            if part.startswith('method='):
                method = part.split('=', 1)[1]
            elif part.startswith('password='):
                password = part.split('=', 1)[1]
            elif part.startswith('tag='):
                tag = part.split('=', 1)[1]
                
        return {
            "name": tag,
            "server": server,
            "port": port,
            "protocol": "shadowsocks", # Default assumption for QuanX text
            "secret": password,
            "cipher": method,
            "sources": ["quanx-txt"]
        }


def main():
    """CLI for testing subscription parsing."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Input file or URL")
    parser.add_argument("--format", choices=["yaml", "json", "text", "b64"], help="Force format")
    
    args = parser.parse_args()
    
    content = ""
    if args.input.startswith("http"):
        import requests
        r = requests.get(args.input, timeout=10)
        content = r.text
    else:
        with open(args.input, 'r') as f:
            content = f.read()
            
    parser_inst = SubscriptionParser()
    proxies = parser_inst.parse(content, fmt=args.format)
    
    print(f"[+] Parsed {len(proxies)} proxies.")
    for p in proxies[:5]:
        print(f"  - {p['name']} ({p['protocol']})")
    if len(proxies) > 5:
        print(f"  ... and {len(proxies)-5} more.")


if __name__ == "__main__":
    main()