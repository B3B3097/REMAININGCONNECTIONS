#!/usr/bin/env python3
"""Advanced Network Utilities for REMAININGCONNECTIONS.

This module provides low-level network tools for deep packet inspection,
DNS resolution over secure channels (DoH), and connection latency benchmarking.
It is designed to support the proxy validation engine with accurate real-world metrics.
"""

from __future__ import annotations

import asyncio
import ipaddress
import json
import logging
import os
import platform
import socket
import ssl
import struct
import time
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urlparse

try:
    import aiohttp
except ImportError:
    aiohttp = None

logger = logging.getLogger("NetworkUtils")


@dataclass
class DNSResponse:
    """Result of a DNS query."""
    hostname: str
    ip_address: str
    ttl: int
    provider: str
    query_time_ms: float


@dataclass
class LatencyResult:
    """Result of a latency measurement."""
    host: str
    port: int
    tcp_latency_ms: Optional[float]
    tls_handshake_ms: Optional[float]
    status: str  # success, timeout, error, refused


class DNSOverHTTPS:
    """Performs DNS resolution using Cloudflare or Google DoH."""

    CLOUDFLARE_URL = "https://1.1.1.1/dns-query"
    GOOGLE_URL = "https://dns.google/resolve"

    def __init__(self, provider: str = "cloudflare"):
        self.provider = provider
        if provider == "cloudflare":
            self.url = self.CLOUDFLARE_URL
            self.headers = {"Accept": "application/dns-json"}
        elif provider == "google":
            self.url = self.GOOGLE_URL
            self.headers = {"Accept": "application/json"}
        else:
            raise ValueError(f"Unsupported DoH provider: {provider}")

    async def resolve(self, hostname: str) -> Optional[DNSResponse]:
        """Resolve hostname using DoH."""
        if not aiohttp:
            logger.warning("aiohttp not installed. Using standard socket.")
            return await self._fallback_resolve(hostname)

        start_time = time.perf_counter()
        
        try:
            async with aiohttp.ClientSession() as session:
                params = {"name": hostname, "type": "A"} if self.provider == "google" else None
                
                async with session.get(self.url, headers=self.headers, params=params, timeout=5) as resp:
                    if resp.status != 200:
                        return None
                    
                    data = await resp.json()
                    
                    if self.provider == "cloudflare":
                        answers = data.get("Answer", [])
                    else:
                        answers = data.get("Answer", [])
                        
                    if not answers:
                        return None
                        
                    ip = answers[0].get("data")
                    ttl = answers[0].get("TTL", 300)
                    
                    elapsed = (time.perf_counter() - start_time) * 1000
                    
                    return DNSResponse(
                        hostname=hostname,
                        ip_address=ip,
                        ttl=ttl,
                        provider=self.provider,
                        query_time_ms=round(elapsed, 2)
                    )
                    
        except Exception as e:
            logger.error(f"DoH resolution failed for {hostname}: {e}")
            return await self._fallback_resolve(hostname)

    @staticmethod
    async def _fallback_resolve(hostname: str) -> Optional[DNSResponse]:
        """Standard socket-based fallback."""
        start_time = time.perf_counter()
        try:
            addr_info = await asyncio.get_event_loop().getaddrinfo(hostname, None, family=socket.AF_INET)
            ip = addr_info[0][4][0]
            elapsed = (time.perf_counter() - start_time) * 1000
            return DNSResponse(
                hostname=hostname,
                ip_address=ip,
                ttl=0,
                provider="system",
                query_time_ms=round(elapsed, 2)
            )
        except Exception as e:
            logger.error(f"Fallback resolution failed: {e}")
            return None


class ConnectionProfiler:
    """Measures TCP and TLS latencies for proxy endpoints."""

    @staticmethod
    async def check_tcp_latency(host: str, port: int, timeout: float = 5.0) -> float:
        """Measure raw TCP connection time."""
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout
            )
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, OSError):
            return False

    @staticmethod
    async def get_tls_fingerprint(host: str, port: int, sni: str = None, timeout: float = 5.0) -> Dict[str, Any]:
        """
        Perform a fake TLS handshake to extract server info.
        Returns certificate details and supported ciphers.
        """
        result = {
            "success": False,
            "cert_subject": None,
            "cert_issuer": None,
            "supported_ciphers": [],
            "error": None
        }

        try:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE
            
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port, ssl=context, server_hostname=sni or host),
                timeout=timeout
            )
            
            try:
                # Get peer certificate
                cert = writer.get_extra_info("peercert")
                if cert:
                    result["cert_subject"] = cert.get("subject", ())
                    result["cert_issuer"] = cert.get("issuer", ())
                
                # Get cipher info
                cipher = writer.get_extra_info("cipher")
                if cipher:
                    result["supported_ciphers"].append(cipher[0])
                
                result["success"] = True
            finally:
                writer.close()
                await writer.wait_closed()
                
        except Exception as e:
            result["error"] = str(e)
            
        return result

    @staticmethod
    async def benchmark_proxy(proxy: Dict[str, Any], timeout: float = 5.0) -> LatencyResult:
        """
        Benchmark a single proxy entry.
        """
        host = proxy.get("host") or proxy.get("server")
        port = proxy.get("port")
        protocol = proxy.get("protocol", "").lower()
        
        if not host or not port:
            return LatencyResult(host="unknown", port=0, tcp_latency_ms=None, tls_handshake_ms=None, status="invalid_config")

        try:
            # 1. TCP Check
            start = time.perf_counter()
            valid = await ConnectionProfiler.check_tcp_latency(host, port, timeout)
            tcp_time = (time.perf_counter() - start) * 1000
            
            if not valid:
                return LatencyResult(host=host, port=port, tcp_latency_ms=round(tcp_time), tls_handshake_ms=None, status="tcp_refused")

            # 2. TLS Check (if applicable)
            tls_time = None
            if protocol in ("vless", "vmess", "trojan", "hysteria2", "tuic"):
                # Only check TLS if we suspect it's used (usually port 443)
                if port == 443:
                    tls_start = time.perf_counter()
                    fp = await ConnectionProfiler.get_tls_fingerprint(host, port, sni=proxy.get("sni"))
                    tls_time = (time.perf_counter() - tls_start) * 1000
                    
                    if not fp["success"]:
                        # TLS failed but TCP worked
                        pass 
                    else:
                        # Store extra info in proxy dict if needed
                        proxy["_tls_info"] = fp

            return LatencyResult(
                host=host,
                port=port,
                tcp_latency_ms=round(tcp_time, 2),
                tls_handshake_ms=round(tls_time, 2) if tls_time else None,
                status="working"
            )
            
        except Exception as e:
            return LatencyResult(host=host, port=port, tcp_latency_ms=None, tls_handshake_ms=None, status=f"error:{str(e)}")


class IPGeolocator:
    """Simple geolocation heuristics based on IP ranges (Mock implementation)."""
    
    # In a real scenario, this would call an API like ip-api.com
    # Here we simulate based on known ranges or return generic data
    
    KNOWN_RANGES = {
        "149.154.x.x": "Russia (DC)",
        "91.108.x.x": "Russia (DC)",
        "104.x.x.x": "Cloudflare US",
        "172.67.x.x": "Cloudflare US",
    }

    def locate_ip(self, ip_str: str) -> Dict[str, Any]:
        try:
            ip = ipaddress.ip_address(ip_str)
            
            # Simple heuristic for Telegram DCs
            if str(ip).startswith("149.154") or str(ip).startswith("91.108"):
                return {"country": "RU", "region": "Telegram DC", "isp": "Telegram FZ-LLC"}
            
            # General placeholder
            return {
                "country": "Unknown",
                "region": "N/A",
                "isp": "Private/Bogon" if ip.is_private else "Public"
            }
        except ValueError:
            return {"error": "Invalid IP"}

def main():
    """CLI for network diagnostics."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Target host")
    parser.add_argument("--port", type=int, required=True, help="Target port")
    parser.add_argument("--mode", choices=["dns", "latency", "tls"], default="latency", help="Test mode")
    
    args = parser.parse_args()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    if args.mode == "dns":
        resolver = DNSOverHTTPS("cloudflare")
        print(f"[*] Resolving {args.host}...")
        result = loop.run_until_complete(resolver.resolve(args.host))
        if result:
            print(json.dumps({
                "ip": result.ip_address,
                "ttl": result.ttl,
                "time_ms": result.query_time_ms
            }, indent=2))
        else:
            print("[-] Resolution failed")
            
    elif args.mode == "latency":
        proxy = {"host": args.host, "port": args.port}
        profiler = ConnectionProfiler()
        print(f"[*] Benchmarking {args.host}:{args.port}...")
        result = loop.run_until_complete(profiler.benchmark_proxy(proxy))
        print(json.dumps({
            "status": result.status,
            "tcp_ms": result.tcp_latency_ms,
            "tls_ms": result.tls_handshake_ms
        }, indent=2))
        
    elif args.mode == "tls":
        print(f"[*] Checking TLS fingerprint for {args.host}:{args.port}...")
        profiler = ConnectionProfiler()
        result = loop.run_until_complete(profiler.get_tls_fingerprint(args.host, args.port))
        print(json.dumps(result, indent=2, default=str))

if __name__ == "__main__":
    main()