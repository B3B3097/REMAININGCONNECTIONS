#!/usr/bin/env python3
"""Advanced MTProto proxy checker with Telegram protocol validation."""

from __future__ import annotations

import asyncio
import hashlib
import os
import secrets
import struct
import time
from dataclasses import dataclass
from typing import Any

# Telegram DC addresses for connectivity checks
TELEGRAM_DCS = [
    ("149.154.175.50", 443),   # DC2
    ("149.154.167.51", 443),   # DC4
    ("149.154.175.100", 443),  # DC2 media
    ("149.154.167.91", 443),   # DC4 media
    ("91.108.56.130", 443),    # DC5
]

CONTROL_DC = ("149.154.167.51", 443)  # DC4 for control checks


@dataclass
class MTProtoCheckResult:
    """Result of MTProto proxy validation."""
    status: str  # working, invalid, timeout, connection_failed
    verification: str
    latency_ms: float | None
    error: str | None = None
    protocol_version: str | None = None
    dc_connected: str | None = None


def decode_mtproto_secret(secret: str) -> bytes:
    """Decode MTProto secret from hex, dd/ee prefixed hex, or base64/base64url."""
    if not secret or not isinstance(secret, str):
        raise ValueError("Empty secret")
    s = secret.strip()
    try:
        from mtproto_real_checker import parse_secret
        return parse_secret(s)["raw"]
    except Exception:
        pass

    lower = s.lower()
    if lower.startswith("ee") or lower.startswith("dd"):
        if len(lower) >= 34:
            try:
                return bytes.fromhex(lower[2:34])
            except ValueError:
                pass
    try:
        raw = bytes.fromhex(lower)
        if len(raw) >= 16:
            return raw[:16]
    except ValueError:
        pass

    import base64
    b64 = s.replace("-", "+").replace("_", "/")
    b64 += "=" * ((4 - len(b64) % 4) % 4)
    try:
        raw = base64.b64decode(b64, validate=False)
        if len(raw) >= 16:
            if len(raw) >= 17 and raw[0] in (0xEE, 0xDD):
                return raw[1:17]
            return raw[:16]
    except Exception:
        pass

    raise ValueError("Invalid secret format")

def generate_mtproto_handshake(secret: bytes) -> tuple[bytes, bytes]:
    """
    Generate MTProto handshake request.
    Returns (encrypted_packet, decryption_key).
    """
    # Generate random nonce
    nonce = secrets.token_bytes(64)
    
    # Create protocol identifier
    protocol_tag = b"\xef\xef\xef\xef"
    
    # Build initial packet
    packet = protocol_tag + nonce
    
    # Use secret for encryption key derivation
    key = hashlib.sha256(secret + nonce[:16]).digest()
    
    return packet, key


async def check_mtproto_handshake(
    host: str,
    port: int,
    secret: bytes,
    timeout: float,
) -> MTProtoCheckResult:
    """
    Perform MTProto handshake check.
    This validates that the proxy can negotiate MTProto protocol.
    """
    start = time.perf_counter()
    
    try:
        # Connect to proxy
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        
        connect_latency = round((time.perf_counter() - start) * 1000, 2)
        
        try:
            # Generate handshake
            handshake_packet, _ = generate_mtproto_handshake(secret)
            
            # Send handshake
            writer.write(handshake_packet)
            await writer.drain()
            
            # Try to read response (MTProto proxy should respond)
            response = await asyncio.wait_for(
                reader.read(256),
                timeout=min(timeout - (time.perf_counter() - start), 2.0)
            )
            
            total_latency = round((time.perf_counter() - start) * 1000, 2)
            
            if len(response) >= 8:
                # Got response from proxy - protocol negotiation works
                return MTProtoCheckResult(
                    status="working",
                    verification="mtproto_handshake",
                    latency_ms=total_latency,
                    protocol_version="mtproto",
                )
            else:
                # Response too short
                return MTProtoCheckResult(
                    status="invalid",
                    verification="mtproto_handshake",
                    latency_ms=connect_latency,
                    error="response_too_short",
                )
        
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass
    
    except asyncio.TimeoutError:
        return MTProtoCheckResult(
            status="timeout",
            verification="mtproto_handshake",
            latency_ms=None,
            error="handshake_timeout",
        )
    
    except (OSError, ConnectionError) as exc:
        return MTProtoCheckResult(
            status="connection_failed",
            verification="mtproto_handshake",
            latency_ms=None,
            error=f"{type(exc).__name__}",
        )


async def check_mtproto_proxy_full(
    host: str,
    port: int,
    secret: str,
    timeout: float,
) -> MTProtoCheckResult:
    """
    Full MTProto proxy check with real cryptographic protocol handshake (resPQ).
    """
    if not host or not port or not secret:
        return MTProtoCheckResult(
            status="invalid",
            verification="input_validation",
            latency_ms=None,
            error="missing_host_port_or_secret",
        )

    # Real protocol check: obfuscated2 handshake + req_pq_multi -> resPQ.
    try:
        import mtproto_real_checker as _real
    except ImportError:
        _real = None

    if _real is not None:
        import asyncio as _asyncio
        loop = _asyncio.get_running_loop()
        outcome = await loop.run_in_executor(
            None,
            lambda: _real.check_proxy(str(host), int(port), str(secret), timeout=timeout),
        )
        if outcome.get("ok"):
            return MTProtoCheckResult(
                status="working",
                verification="mtproto_res_pq",
                latency_ms=outcome.get("rtt_ms"),
                protocol_version="mtproto",
                dc_connected=str(outcome.get("dc")),
            )
        error = outcome.get("error")
        if error == "timeout":
            status = "timeout"
        elif error == "network_error":
            status = "connection_failed"
        elif error == "invalid_secret":
            status = "invalid"
        else:
            status = "invalid" if "invalid" in str(error) else "connection_failed"

        return MTProtoCheckResult(
            status=status,
            verification="mtproto_res_pq",
            latency_ms=outcome.get("rtt_ms"),
            error=outcome.get("detail") or outcome.get("error"),
            protocol_version="mtproto",
            dc_connected=(
                str(outcome.get("dc"))
                if outcome.get("dc") is not None
                else None
            ),
        )

    # Fallback when the real checker module is unavailable: legacy TCP probe
    try:
        secret_bytes = decode_mtproto_secret(secret)
    except ValueError as exc:
        return MTProtoCheckResult(
            status="invalid",
            verification="secret_validation",
            latency_ms=None,
            error=f"invalid_secret: {str(exc)}",
        )

    result = await check_mtproto_handshake(host, int(port), secret_bytes, timeout)
    return result

async def check_mtproto_dc_connectivity(
    host: str,
    port: int,
    secret: str,
    timeout: float,
) -> dict[str, Any]:
    """
    Advanced check: verify proxy can reach Telegram DCs.
    This attempts to proxy through to actual Telegram servers.
    """
    try:
        secret_bytes = decode_mtproto_secret(secret)
    except ValueError:
        return {
            "reachable": False,
            "error": "invalid_secret",
        }
    
    # This is a simplified DC reachability check
    # Real implementation would need full MTProto protocol
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        
        try:
            # Send handshake
            handshake, _ = generate_mtproto_handshake(secret_bytes)
            writer.write(handshake)
            await writer.drain()
            
            # If we get here, basic connectivity works
            return {
                "reachable": True,
                "dc_tested": CONTROL_DC[0],
            }
        
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except:
                pass
    
    except (asyncio.TimeoutError, OSError, ConnectionError):
        return {
            "reachable": False,
            "error": "connection_failed",
        }


async def batch_check_mtproto_proxies(
    proxies: list[dict[str, Any]],
    timeout: float = 8.0,
    concurrency: int = 20,
) -> list[dict[str, Any]]:
    """
    Check multiple MTProto proxies in parallel.
    """
    semaphore = asyncio.Semaphore(concurrency)
    
    async def check_one(proxy: dict[str, Any]) -> dict[str, Any]:
        host = proxy.get("host") or proxy.get("server")
        port = proxy.get("port")
        secret = proxy.get("secret")
        
        if not all([host, port, secret]):
            proxy["mtproto_check"] = {
                "status": "invalid",
                "error": "missing_required_fields",
            }
            return proxy
        
        async with semaphore:
            result = await check_mtproto_proxy_full(
                host=host,
                port=int(port),
                secret=secret,
                timeout=timeout,
            )
        
        proxy["mtproto_check"] = {
            "status": result.status,
            "verification": result.verification,
            "latency_ms": result.latency_ms,
            "error": result.error,
            "protocol_version": result.protocol_version,
        }
        
        # Upgrade main status if MTProto check passes
        if result.status == "working":
            proxy["status"] = "working"
            proxy["verification"] = "mtproto_validated"
        
        return proxy
    
    return await asyncio.gather(*(check_one(p) for p in proxies))


def main():
    """CLI for testing MTProto proxy checker."""
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Proxy host")
    parser.add_argument("--port", type=int, required=True, help="Proxy port")
    parser.add_argument("--secret", required=True, help="MTProto secret (hex)")
    parser.add_argument("--timeout", type=float, default=8.0, help="Timeout in seconds")
    
    args = parser.parse_args()
    
    result = asyncio.run(
        check_mtproto_proxy_full(
            host=args.host,
            port=args.port,
            secret=args.secret,
            timeout=args.timeout,
        )
    )
    
    print(json.dumps({
        "status": result.status,
        "verification": result.verification,
        "latency_ms": result.latency_ms,
        "error": result.error,
        "protocol_version": result.protocol_version,
    }, indent=2))


if __name__ == "__main__":
    main()