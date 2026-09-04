#!/usr/bin/env python3
"""Configuration Importer for REMAININGCONNECTIONS.

Supports importing proxies from various popular formats including:
- Clash YAML (.yml/.yaml)
- V2Ray JSON (.json)
- Surge Configurations (.conf)
- Raw URI Lists (.txt)
- Base64 Encoded Strings

This allows consolidating known working proxies from different clients 
into our unified JSON format.
"""

from __future__ import annotations

import base64
import json
import re
import sys
import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse, unquote

# Default settings
DEFAULT_OUTPUT = "data/imported_proxies.json"


class ProxyNormalizer:
    """Standardizes proxy entries into our internal format."""

    @staticmethod
    def normalize(proxy: dict[str, Any]) -> Optional[dict[str, Any]]:
        """Convert a raw proxy dict to our standard schema."""
        if not proxy:
            return None

        # Extract common fields
        server = proxy.get("server") or proxy.get("address") or proxy.get("host")
        port = proxy.get("port") or proxy.get("server_port")
        
        if not server or not port:
            return None

        protocol = proxy.get("type", "").lower()
        secret = proxy.get("password") or proxy.get("uuid") or proxy.get("secret") or proxy.get("key")
        
        # Determine protocol type
        normalized_proto = ProxyNormalizer._detect_protocol(protocol, proxy)
        
        return {
            "server": server,
            "host": server,
            "port": int(port),
            "protocol": normalized_proto,
            "secret": secret,
            "name": proxy.get("name", f"{normalized_proto}-{server}"),
            "sources": ["import"]
        }

    @staticmethod
    def _detect_protocol(raw_type: str, data: dict) -> str:
        """Map client-specific types to standard protocols."""
        t = raw_type.lower()
        
        if t in ("vless", "vmess"):
            return t
        elif t in ("trojan",):
            return "trojan"
        elif t in ("ss", "shadowsocks"):
            return "shadowsocks"
        elif t in ("socks5", "socks"):
            return "socks5"
        elif t in ("http", "https"):
            return "http"
        else:
            # Fallback based on content
            if "id" in data and "network" in data:
                return "vmess" # Likely v2ray vmess
            if "cipher" in data:
                return "shadowsocks"
            return "unknown"


class ConfigImporter:
    """Main class for parsing and importing configurations."""

    def __init__(self):
        self.normalizer = ProxyNormalizer()

    def import_from_file(self, filepath: str) -> List[dict]:
        """Detect format and import from file."""
        path = Path(filepath)
        ext = path.suffix.lower()
        
        if ext in ('.yml', '.yaml'):
            return self.import_clash(path)
        elif ext == '.json':
            return self.import_v2ray(path)
        elif ext in ('.conf', '.txt'):
            return self.import_text(path)
        else:
            raise ValueError(f"Unsupported file extension: {ext}")

    def import_clash(self, filepath: Path) -> List[dict]:
        """Parse Clash YAML format."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except Exception as e:
            print(f"[Error] Failed to parse YAML: {e}")
            return []

        proxies = config.get('proxies', [])
        results = []
        
        for p in proxies:
            normalized = self.normalizer.normalize(p)
            if normalized:
                results.append(normalized)
                
        print(f"[+] Imported {len(results)} proxies from {filepath.name} (Clash)")
        return results

    def import_v2ray(self, filepath: Path) -> List[dict]:
        """Parse V2Ray JSON format."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                config = json.load(f)
        except Exception as e:
            print(f"[Error] Failed to parse JSON: {e}")
            return []

        outbounds = config.get('outbounds', [])
        results = []
        
        for ob in outbounds:
            tag = ob.get('tag', '')
            proto = ob.get('protocol', '')
            
            if proto in ('vless', 'vmess', 'shadowsocks', 'trojan', 'freedom', 'blackhole'):
                settings = ob.get('settings', {})
                stream_settings = ob.get('streamSettings', {})
                
                # Construct a pseudo-proxy dict
                proxy_data = {
                    "name": tag,
                    "protocol": proto
                }
                
                # Handle specific outbound structures
                if proto == 'vless' or proto == 'vmess':
                    servers = settings.get('vnext', [{}])[0].get('servers', [{}])[0]
                    proxy_data['server'] = settings.get('vnext', [{}])[0].get('address')
                    proxy_data['port'] = settings.get('vnext', [{}])[0].get('port')
                    proxy_data['uuid'] = servers.get('id')
                    
                elif proto == 'shadowsocks':
                    servers = settings.get('servers', [{}])[0]
                    proxy_data['server'] = servers.get('address')
                    proxy_data['port'] = servers.get('port')
                    proxy_data['password'] = servers.get('password')
                    proxy_data['cipher'] = servers.get('method')
                    
                elif proto == 'trojan':
                    servers = settings.get('servers', [{}])[0]
                    proxy_data['server'] = servers.get('address')
                    proxy_data['port'] = servers.get('port')
                    proxy_data['password'] = servers.get('password')

                # Map to normalizer input
                normalized_input = {
                    "name": tag,
                    "type": proto,
                    "server": proxy_data.get('server'),
                    "port": proxy_data.get('port'),
                    "password": proxy_data.get('password'),
                    "uuid": proxy_data.get('uuid'),
                    "secret": proxy_data.get('password') # For trojan/mixed
                }
                
                normalized = self.normalizer.normalize(normalized_input)
                if normalized:
                    results.append(normalized)

        print(f"[+] Imported {len(results)} proxies from {filepath.name} (V2Ray)")
        return results

    def import_text(self, filepath: Path) -> List[dict]:
        """Parse raw text list (URI or Surge style)."""
        content = filepath.read_text(encoding='utf-8')
        lines = content.splitlines()
        results = []
        
        for line in lines:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
                
            # Try URI parsing first
            uri_result = self._parse_uri(line)
            if uri_result:
                results.append(uri_result)
                continue
            
            # Try Surge format: Name = Type, Server, Port, ...
            surge_match = re.match(r'^([^=]+)=\s*(.+)$', line)
            if surge_match:
                name, params = surge_match.groups()
                surgeresult = self._parse_surge_line(name, params)
                if surgeresult:
                    results.append(surgeresult)
        
        print(f"[+] Imported {len(results)} proxies from {filepath.name} (Text)")
        return results

    def _parse_uri(self, uri: str) -> Optional[dict]:
        """Parse a single URI string."""
        try:
            parsed = urlparse(uri)
            
            if parsed.scheme == 'tg':
                return {
                    "server": parsed.query.split('&')[0].split('=')[1] if '=' in parsed.query else None,
                    "protocol": "mtproto",
                    "url": uri
                }
            elif parsed.scheme in ('socks', 'socks5'):
                return {
                    "server": parsed.hostname,
                    "port": parsed.port,
                    "protocol": "socks5",
                    "url": uri
                }
            elif parsed.scheme in ('http', 'https'):
                return {
                    "server": parsed.hostname,
                    "port": parsed.port,
                    "protocol": "http",
                    "url": uri
                }
        except Exception:
            pass
        return None

    def _parse_surge_line(self, name: str, params_str: str) -> Optional[dict]:
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
            "type": stype,
            "password": secret,
            "cipher": cipher
        }

    def run(self, input_path: str, output_path: str = DEFAULT_OUTPUT):
        """Execute the import process."""
        print(f"[*] Starting import from {input_path}")
        
        proxies = self.import_from_file(input_path)
        
        if not proxies:
            print("[!] No valid proxies found.")
            return

        # Deduplicate
        seen = set()
        unique = []
        for p in proxies:
            key = f"{p['server']}:{p['port']}:{p.get('secret','')}"
            if key not in seen:
                seen.add(key)
                unique.append(p)
        
        payload = {
            "generated_at": __import__('datetime').datetime.utcnow().isoformat(),
            "total": len(unique),
            "proxies": unique
        }
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            
        print(f"[+] Saved {len(unique)} unique proxies to {output_path}")


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", help="Input configuration file")
    parser.add_argument("--output", default=DEFAULT_OUTPUT, help="Output JSON file")
    
    args = parser.parse_args()
    
    importer = ConfigImporter()
    importer.run(args.input, args.output)


if __name__ == "__main__":
    main()