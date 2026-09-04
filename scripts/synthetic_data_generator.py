#!/usr/bin/env python3
"""Synthetic Data Generator for REMAININGCONNECTIONS.

Generates realistic fake proxy data to test the dashboard and parsers
without using real, potentially sensitive, production data.

This script creates a JSON file with randomized proxies of various types,
statuses, and latency values.
"""

import json
import os
import sys
import random
import string
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any

# Configuration
OUTPUT_DIR = Path("data")
OUTPUT_FILE = OUTPUT_DIR / "synthetic_proxies_test.json"

PROTOCOLS = ["vless", "vmess", "trojan", "shadowsocks", "mtproto", "socks5", "http"]
SERVER_REGIONS = [
    "US", "DE", "JP", "UK", "FR", "NL", "SG", "CA", "RU", "BR"
]

def generate_random_hex(length: int) -> str:
    """Generate a random hex string."""
    return ''.join(random.choices(string.hexdigits.lower(), k=length))

def generate_vless_proxy() -> Dict[str, Any]:
    """Generate a fake VLESS proxy."""
    domain = f"{random.choice(['cdn', 'worker', 'api'])}-{generate_random_hex(4)}.example.com"
    uuid = generate_random_hex(32) + '-' + generate_random_hex(4) + '-' + generate_random_hex(4) + '-' + generate_random_hex(4) + '-' + generate_random_hex(12)
    
    # Construct URI
    uri = f"vless://{uuid}@{domain}:443?encryption=none&security=tls&sni={domain}&fp=randomized&type=http#VLESS-US-CDN"
    
    return {
        "server": domain,
        "host": domain,
        "port": 443,
        "protocol": "vless",
        "secret": uuid,
        "url": uri,
        "name": f"VLESS-{random.choice(SERVER_REGIONS)}",
        "sources": [{"source": "generator"}],
        "status": random.choice(["working", "working", "working", "unverified", "failed"]),
        "latency_ms": random.randint(20, 800) if random.random() > 0.2 else None
    }

def generate_vmess_proxy() -> Dict[str, Any]:
    """Generate a fake VMess proxy."""
    domain = f"vmess-{generate_random_hex(6)}.cdn.net"
    uuid = generate_random_hex(32) + '-' + generate_random_hex(4) + '-' + generate_random_hex(4) + '-' + generate_random_hex(4) + '-' + generate_random_hex(12)
    
    # Base64 encoded vmess config (simplified representation)
    raw = json.dumps({
        "v": "2",
        "ps": f"VMess-{random.choice(SERVER_REGIONS)}",
        "add": domain,
        "port": "443",
        "id": uuid,
        "aid": "0",
        "net": "ws",
        "type": "none",
        "host": domain,
        "path": "/ws-path",
        "tls": "tls"
    }, separators=(',', ':'))
    
    import base64
    uri = f"vmess://{base64.b64encode(raw.encode()).decode()}"
    
    return {
        "server": domain,
        "host": domain,
        "port": 443,
        "protocol": "vmess",
        "secret": uuid,
        "url": uri,
        "name": f"VMess-{random.choice(SERVER_REGIONS)}",
        "sources": [{"source": "generator"}],
        "status": random.choice(["working", "working", "unverified"]),
        "latency_ms": random.randint(50, 1200)
    }

def generate_trojan_proxy() -> Dict[str, Any]:
    """Generate a fake Trojan proxy."""
    domain = f"trojan-{generate_random_hex(5)}.cloudfront.net"
    password = generate_random_hex(16)
    
    uri = f"trojan://{password}@{domain}:443?sni={domain}#Trojan-DE"
    
    return {
        "server": domain,
        "host": domain,
        "port": 443,
        "protocol": "trojan",
        "secret": password,
        "url": uri,
        "name": f"Trojan-{random.choice(SERVER_REGIONS)}",
        "sources": [{"source": "generator"}],
        "status": random.choice(["working", "failed"]),
        "latency_ms": random.randint(10, 500)
    }

def generate_shadowsocks_proxy() -> Dict[str, Any]:
    """Generate a fake Shadowsocks proxy."""
    domain = f"ss-{generate_random_hex(4)}.local"
    password = generate_random_hex(32)
    
    uri = f"ss://{base64.b64encode(f'aes-256-gcm:{password}@{domain}:8388'.encode()).decode()}#SS-BR"
    
    return {
        "server": domain,
        "host": domain,
        "port": 8388,
        "protocol": "shadowsocks",
        "secret": password,
        "url": uri,
        "name": f"SS-{random.choice(SERVER_REGIONS)}",
        "sources": [{"source": "generator"}],
        "status": random.choice(["working", "working", "failed"]),
        "latency_ms": random.randint(100, 2000)
    }

def generate_mtproto_proxy() -> Dict[str, Any]:
    """Generate a fake MTProto proxy."""
    server = f"{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}.{random.randint(1,255)}"
    port = random.choice([80, 443, 8888])
    secret = "ee" + generate_random_hex(64) # Telegram usually uses ee or dd prefix
    
    uri = f"tg://proxy?server={server}&port={port}&secret={secret}"
    
    return {
        "server": server,
        "host": server,
        "port": port,
        "protocol": "mtproto",
        "secret": secret,
        "url": uri,
        "tg_url": uri,
        "name": f"MTProto-{server}",
        "sources": [{"source": "generator"}],
        "status": random.choice(["working", "unverified", "failed"]),
        "latency_ms": random.randint(50, 1500)
    }

def generate_socks5_proxy() -> Dict[str, Any]:
    """Generate a fake SOCKS5 proxy."""
    server = f"socks-{generate_random_hex(4)}.proxy.net"
    
    uri = f"socks5://{server}:1080"
    
    return {
        "server": server,
        "host": server,
        "port": 1080,
        "protocol": "socks5",
        "url": uri,
        "name": f"SOCKS5-{random.choice(SERVER_REGIONS)}",
        "sources": [{"source": "generator"}],
        "status": random.choice(["working", "failed"]),
        "latency_ms": random.randint(20, 600)
    }

def main():
    """Generate and save synthetic data."""
    generators = [
        (generate_vless_proxy, 10),
        (generate_vmess_proxy, 10),
        (generate_trojan_proxy, 10),
        (generate_shadowsocks_proxy, 10),
        (generate_mtproto_proxy, 15),
        (generate_socks5_proxy, 5),
    ]
    
    all_proxies = []
    
    print("[*] Generating synthetic data...")
    
    for gen_func, count in generators:
        for _ in range(count):
            proxy = gen_func()
            all_proxies.append(proxy)
            
    # Shuffle to mix protocols
    random.shuffle(all_proxies)
    
    payload = {
        "generated_at": datetime.utcnow().isoformat(),
        "total": len(all_proxies),
        "description": "Synthetic data for testing purposes",
        "proxies": all_proxies
    }
    
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
        
    print(f"[+] Generated {len(all_proxies)} proxies.")
    print(f"[+] Saved to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()