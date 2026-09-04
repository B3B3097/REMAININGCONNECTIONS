#!/usr/bin/env python3
"""Export and convert proxy configurations to various client formats."""

from __future__ import annotations

import base64
import json
import yaml
from pathlib import Path
from typing import Any
from urllib.parse import quote, urlencode


class ConfigExporter:
    """Export proxy configs to different client formats."""
    
    def __init__(self, proxies: list[dict[str, Any]]):
        self.proxies = proxies
    
    def to_uri_list(self) -> list[str]:
        """Export as plain URI list."""
        uris = []
        for proxy in self.proxies:
            uri = proxy.get("url")
            if uri:
                uris.append(uri)
        return uris
    
    def to_base64_subscription(self) -> str:
        """Export as base64-encoded subscription."""
        uris = self.to_uri_list()
        content = "\n".join(uris)
        encoded = base64.b64encode(content.encode("utf-8")).decode("ascii")
        return encoded
    
    def to_clash_yaml(self) -> str:
        """Export to Clash YAML format."""
        clash_proxies = []
        
        for idx, proxy in enumerate(self.proxies):
            protocol = proxy.get("protocol", "").lower()
            server = proxy.get("host") or proxy.get("server")
            port = proxy.get("port")
            
            if not server or not port:
                continue
            
            name = f"{protocol}-{idx}"
            
            clash_proxy: dict[str, Any] = {
                "name": name,
                "type": protocol,
                "server": server,
                "port": int(port),
            }
            
            if protocol == "socks5":
                clash_proxy["type"] = "socks5"
                clash_proxy["udp"] = True
            
            elif protocol == "http":
                clash_proxy["type"] = "http"
            
            elif protocol == "ss" or protocol == "shadowsocks":
                clash_proxy["type"] = "ss"
                clash_proxy["cipher"] = "chacha20-ietf-poly1305"
                clash_proxy["password"] = "password"
            
            elif protocol == "trojan":
                clash_proxy["type"] = "trojan"
                clash_proxy["password"] = proxy.get("secret", "password")
                clash_proxy["sni"] = server
                clash_proxy["skip-cert-verify"] = False
            
            elif protocol in ("vless", "vmess"):
                # Clash Meta supports VLESS/VMess
                clash_proxy["type"] = protocol
                clash_proxy["uuid"] = proxy.get("uuid", "uuid-placeholder")
                clash_proxy["tls"] = True
                clash_proxy["skip-cert-verify"] = False
            
            clash_proxies.append(clash_proxy)
        
        config = {
            "proxies": clash_proxies,
            "proxy-groups": [
                {
                    "name": "auto",
                    "type": "url-test",
                    "proxies": [p["name"] for p in clash_proxies],
                    "url": "https://www.gstatic.com/generate_204",
                    "interval": 300,
                }
            ],
        }
        
        return yaml.dump(config, allow_unicode=True, sort_keys=False)
    
    def to_v2ray_json(self) -> str:
        """Export to V2Ray JSON format."""
        outbounds = []
        
        for idx, proxy in enumerate(self.proxies):
            protocol = proxy.get("protocol", "").lower()
            server = proxy.get("host") or proxy.get("server")
            port = proxy.get("port")
            
            if not server or not port:
                continue
            
            tag = f"{protocol}-{idx}"
            
            if protocol == "vless":
                outbound = {
                    "protocol": "vless",
                    "tag": tag,
                    "settings": {
                        "vnext": [{
                            "address": server,
                            "port": int(port),
                            "users": [{
                                "id": "uuid-placeholder",
                                "encryption": "none",
                            }]
                        }]
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "tls",
                    }
                }
            
            elif protocol == "vmess":
                outbound = {
                    "protocol": "vmess",
                    "tag": tag,
                    "settings": {
                        "vnext": [{
                            "address": server,
                            "port": int(port),
                            "users": [{
                                "id": "uuid-placeholder",
                                "alterId": 0,
                                "security": "auto",
                            }]
                        }]
                    },
                }
            
            elif protocol == "shadowsocks" or protocol == "ss":
                outbound = {
                    "protocol": "shadowsocks",
                    "tag": tag,
                    "settings": {
                        "servers": [{
                            "address": server,
                            "port": int(port),
                            "method": "chacha20-ietf-poly1305",
                            "password": "password",
                        }]
                    },
                }
            
            elif protocol == "trojan":
                outbound = {
                    "protocol": "trojan",
                    "tag": tag,
                    "settings": {
                        "servers": [{
                            "address": server,
                            "port": int(port),
                            "password": proxy.get("secret", "password"),
                        }]
                    },
                    "streamSettings": {
                        "network": "tcp",
                        "security": "tls",
                    }
                }
            
            elif protocol == "socks5":
                outbound = {
                    "protocol": "socks",
                    "tag": tag,
                    "settings": {
                        "servers": [{
                            "address": server,
                            "port": int(port),
                        }]
                    },
                }
            
            else:
                continue
            
            outbounds.append(outbound)
        
        config = {
            "log": {"loglevel": "warning"},
            "inbounds": [{
                "port": 1080,
                "protocol": "socks",
                "settings": {"udp": True}
            }],
            "outbounds": outbounds + [{
                "protocol": "freedom",
                "tag": "direct"
            }],
        }
        
        return json.dumps(config, indent=2, ensure_ascii=False)
    
    def to_singbox_json(self) -> str:
        """Export to sing-box JSON format."""
        outbounds = []
        
        for idx, proxy in enumerate(self.proxies):
            protocol = proxy.get("protocol", "").lower()
            server = proxy.get("host") or proxy.get("server")
            port = proxy.get("port")
            
            if not server or not port:
                continue
            
            tag = f"{protocol}-{idx}"
            
            if protocol == "vless":
                outbound = {
                    "type": "vless",
                    "tag": tag,
                    "server": server,
                    "server_port": int(port),
                    "uuid": "uuid-placeholder",
                    "tls": {
                        "enabled": True,
                        "server_name": server,
                    }
                }
            
            elif protocol == "vmess":
                outbound = {
                    "type": "vmess",
                    "tag": tag,
                    "server": server,
                    "server_port": int(port),
                    "uuid": "uuid-placeholder",
                    "security": "auto",
                }
            
            elif protocol == "shadowsocks" or protocol == "ss":
                outbound = {
                    "type": "shadowsocks",
                    "tag": tag,
                    "server": server,
                    "server_port": int(port),
                    "method": "chacha20-ietf-poly1305",
                    "password": "password",
                }
            
            elif protocol == "trojan":
                outbound = {
                    "type": "trojan",
                    "tag": tag,
                    "server": server,
                    "server_port": int(port),
                    "password": proxy.get("secret", "password"),
                    "tls": {
                        "enabled": True,
                        "server_name": server,
                    }
                }
            
            elif protocol == "socks5":
                outbound = {
                    "type": "socks",
                    "tag": tag,
                    "server": server,
                    "server_port": int(port),
                }
            
            else:
                continue
            
            outbounds.append(outbound)
        
        config = {
            "log": {"level": "warn"},
            "inbounds": [{
                "type": "mixed",
                "listen": "127.0.0.1",
                "listen_port": 1080,
            }],
            "outbounds": outbounds + [{
                "type": "direct",
                "tag": "direct"
            }],
        }
        
        return json.dumps(config, indent=2, ensure_ascii=False)
    
    def to_quantumultx(self) -> str:
        """Export to QuantumultX format."""
        lines = ["[server_local]", ""]
        
        for idx, proxy in enumerate(self.proxies):
            protocol = proxy.get("protocol", "").lower()
            server = proxy.get("host") or proxy.get("server")
            port = proxy.get("port")
            
            if not server or not port:
                continue
            
            tag = f"{protocol}-{idx}"
            
            if protocol == "shadowsocks" or protocol == "ss":
                line = f"shadowsocks={server}:{port}, method=chacha20-ietf-poly1305, password=password, tag={tag}"
            
            elif protocol == "vmess":
                line = f"vmess={server}:{port}, method=chacha20-ietf-poly1305, password=uuid-placeholder, tag={tag}"
            
            elif protocol == "trojan":
                line = f"trojan={server}:{port}, password={proxy.get('secret', 'password')}, tag={tag}"
            
            elif protocol == "http":
                line = f"http={server}:{port}, tag={tag}"
            
            elif protocol == "socks5":
                line = f"socks5={server}:{port}, tag={tag}"
            
            else:
                continue
            
            lines.append(line)
        
        return "\n".join(lines)
    
    def to_surge(self) -> str:
        """Export to Surge format."""
        lines = ["[Proxy]", ""]
        
        for idx, proxy in enumerate(self.proxies):
            protocol = proxy.get("protocol", "").lower()
            server = proxy.get("host") or proxy.get("server")
            port = proxy.get("port")
            
            if not server or not port:
                continue
            
            name = f"{protocol}-{idx}"
            
            if protocol == "shadowsocks" or protocol == "ss":
                line = f"{name} = ss, {server}, {port}, encrypt-method=chacha20-ietf-poly1305, password=password"
            
            elif protocol == "vmess":
                line = f"{name} = vmess, {server}, {port}, username=uuid-placeholder"
            
            elif protocol == "trojan":
                line = f"{name} = trojan, {server}, {port}, password={proxy.get('secret', 'password')}"
            
            elif protocol == "http":
                line = f"{name} = http, {server}, {port}"
            
            elif protocol == "socks5":
                line = f"{name} = socks5, {server}, {port}"
            
            else:
                continue
            
            lines.append(line)
        
        return "\n".join(lines)


def main():
    """CLI for config exporter."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="Input JSON file with proxies")
    parser.add_argument(
        "--format",
        choices=["uri", "base64", "clash", "v2ray", "singbox", "quantumult", "surge"],
        required=True,
        help="Export format",
    )
    parser.add_argument("--output", type=Path, help="Output file (default: stdout)")
    parser.add_argument(
        "--filter-working",
        action="store_true",
        help="Export only working proxies",
    )
    
    args = parser.parse_args()
    
    # Load proxies
    data = json.loads(args.input.read_text(encoding="utf-8"))
    proxies = data.get("proxies", [])
    
    # Filter if requested
    if args.filter_working:
        proxies = [p for p in proxies if p.get("status") == "working"]
    
    # Export
    exporter = ConfigExporter(proxies)
    
    if args.format == "uri":
        result = "\n".join(exporter.to_uri_list())
    elif args.format == "base64":
        result = exporter.to_base64_subscription()
    elif args.format == "clash":
        result = exporter.to_clash_yaml()
    elif args.format == "v2ray":
        result = exporter.to_v2ray_json()
    elif args.format == "singbox":
        result = exporter.to_singbox_json()
    elif args.format == "quantumult":
        result = exporter.to_quantumultx()
    elif args.format == "surge":
        result = exporter.to_surge()
    else:
        parser.error(f"Unsupported format: {args.format}")
    
    # Save or print
    if args.output:
        args.output.write_text(result, encoding="utf-8")
        print(f"Exported {len(proxies)} proxies to {args.output}")
    else:
        print(result)


if __name__ == "__main__":
    main()