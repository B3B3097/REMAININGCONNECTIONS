#!/usr/bin/env python3
"""Strict network validation helpers for Telegram and Xray-compatible proxies."""

from __future__ import annotations

import asyncio
import base64
import ipaddress
import json
import os
import re
import shutil
import socket
import subprocess
import tempfile
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

SUPPORTED_XRAY_PROTOCOLS = {
    "vless", "vmess", "ss", "shadowsocks", "trojan", "hysteria2", "hy2", "tuic",
}
CONTROL_HOST = os.getenv("PROXY_CHECK_HOST", "www.gstatic.com")
CONTROL_PORT = int(os.getenv("PROXY_CHECK_PORT", "443"))
MAX_CONFIG_SIZE = 2_000_000


@dataclass
class CheckResult:
    status: str
    verification: str
    latency_ms: float | None
    error: str | None = None
    detail: str | None = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "verification": self.verification,
            "latency_ms": self.latency_ms,
            "error": self.error,
            "detail": self.detail,
        }


def utc_timestamp() -> str:
    import datetime

    return datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")


def normalize_base64(value: str) -> bytes:
    value = value.strip().replace("-", "+").replace("_", "/")
    value += "=" * (-len(value) % 4)
    return base64.b64decode(value, validate=False)


def is_valid_host(host: str) -> bool:
    if not host or len(host) > 253 or any(ch.isspace() for ch in host):
        return False
    try:
        ipaddress.ip_address(host.strip("[]"))
        return True
    except ValueError:
        return bool(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?", host))


def parse_host_port(host: str | None, port: str | int | None) -> tuple[str, int] | None:
    if not host or port is None or not is_valid_host(host):
        return None
    try:
        number = int(port)
    except (TypeError, ValueError):
        return None
    if not 1 <= number <= 65535:
        return None
    return host.strip("[]"), number


async def resolve_host(host: str, port: int, timeout: float) -> bool:
    try:
        records = await asyncio.wait_for(
            asyncio.get_running_loop().getaddrinfo(host, port, type=socket.SOCK_STREAM),
            timeout=timeout,
        )
        return bool(records)
    except (OSError, asyncio.TimeoutError):
        return False


async def open_tcp(host: str, port: int, timeout: float) -> tuple[asyncio.StreamReader, asyncio.StreamWriter, float]:
    start = time.perf_counter()
    reader, writer = await asyncio.wait_for(asyncio.open_connection(host, port), timeout=timeout)
    return reader, writer, round((time.perf_counter() - start) * 1000, 2)


async def close_writer(writer: asyncio.StreamWriter | None) -> None:
    if writer is None:
        return
    writer.close()
    try:
        await writer.wait_closed()
    except (ConnectionError, OSError):
        pass


async def check_socks5(host: str, port: int, timeout: float) -> CheckResult:
    writer = None
    try:
        reader, writer, latency = await open_tcp(host, port, timeout)
        writer.write(b"\x05\x01\x00")
        await writer.drain()
        reply = await asyncio.wait_for(reader.readexactly(2), timeout=timeout)
        if reply != b"\x05\x00":
            return CheckResult("invalid", "socks5_handshake", latency, "socks5_auth_or_protocol_rejected")
        host_bytes = CONTROL_HOST.encode("idna")
        request = b"\x05\x01\x00\x03" + bytes([len(host_bytes)]) + host_bytes + CONTROL_PORT.to_bytes(2, "big")
        writer.write(request)
        await writer.drain()
        header = await asyncio.wait_for(reader.readexactly(4), timeout=timeout)
        if header[0] != 5 or header[1] != 0:
            return CheckResult("handshake_failed", "socks5_connect", latency, f"socks5_reply_{header[1]}")
        address_length = 4 if header[3] == 1 else 16 if header[3] == 4 else None
        if header[3] == 3:
            address_length = (await asyncio.wait_for(reader.readexactly(1), timeout=timeout))[0]
        if address_length is None:
            return CheckResult("invalid", "socks5_connect", latency, "socks5_invalid_address_type")
        await asyncio.wait_for(reader.readexactly(address_length + 2), timeout=timeout)
        return CheckResult("working", "socks5_connect", latency)
    except asyncio.TimeoutError:
        return CheckResult("timeout", "socks5_handshake", None, "timeout")
    except (OSError, asyncio.IncompleteReadError) as exc:
        return CheckResult("connection_failed", "socks5_handshake", None, type(exc).__name__)
    finally:
        await close_writer(writer)


async def check_http_proxy(host: str, port: int, timeout: float) -> CheckResult:
    writer = None
    try:
        reader, writer, latency = await open_tcp(host, port, timeout)
        request = (
            f"CONNECT {CONTROL_HOST}:{CONTROL_PORT} HTTP/1.1\r\n"
            f"Host: {CONTROL_HOST}:{CONTROL_PORT}\r\n"
            "Proxy-Connection: close\r\n\r\n"
        ).encode("ascii")
        writer.write(request)
        await writer.drain()
        response = await asyncio.wait_for(reader.readuntil(b"\r\n\r\n"), timeout=timeout)
        first_line = response.split(b"\r\n", 1)[0]
        if not re.match(rb"HTTP/\d(?:\.\d)? 2\d\d\b", first_line):
            return CheckResult("handshake_failed", "http_connect", latency, first_line.decode("latin1", "replace")[:160])
        return CheckResult("working", "http_connect", latency)
    except asyncio.TimeoutError:
        return CheckResult("timeout", "http_connect", None, "timeout")
    except (OSError, asyncio.IncompleteReadError) as exc:
        return CheckResult("connection_failed", "http_connect", None, type(exc).__name__)
    finally:
        await close_writer(writer)


def parse_xray_uri(uri: str) -> tuple[str, dict[str, Any]] | None:
    uri = uri.strip()
    if not uri or len(uri) > 8192:
        return None
    parsed = urlparse(uri)
    scheme = parsed.scheme.lower()
    if scheme not in SUPPORTED_XRAY_PROTOCOLS:
        return None

    if scheme == "vmess":
        try:
            payload = json.loads(normalize_base64(uri.split("://", 1)[1]).decode("utf-8"))
            host_port = parse_host_port(payload.get("add"), payload.get("port"))
            if not host_port or not payload.get("id"):
                return None
            host, port = host_port
            stream = {
                "network": payload.get("net", "tcp"),
                "security": payload.get("tls", "") if payload.get("tls") != "none" else "",
            }
            if payload.get("host"):
                stream["wsSettings"] = {"headers": {"Host": payload["host"]}}
            if payload.get("path"):
                stream.setdefault("wsSettings", {})["path"] = payload["path"]
            outbound = {
                "protocol": "vmess",
                "settings": {"vnext": [{"address": host, "port": port, "users": [{
                    "id": payload["id"], "alterId": int(payload.get("aid", 0)), "security": payload.get("scy", "auto"),
                }]}]},
                "streamSettings": stream,
            }
            return "vmess", outbound
        except (ValueError, UnicodeDecodeError, json.JSONDecodeError, KeyError):
            return None

    query = parse_qs(parsed.query, keep_blank_values=True)
    host_port = parse_host_port(parsed.hostname, parsed.port)
    if not host_port:
        return None
    host, port = host_port
    user = unquote(parsed.username or "")
    stream: dict[str, Any] = {"network": query.get("type", ["tcp"])[0]}
    security = query.get("security", ["tls" if scheme in {"trojan", "hysteria2", "hy2", "tuic"} else "none"])[0]
    if security and security != "none":
        stream["security"] = security
        tls_settings: dict[str, Any] = {}
        sni = query.get("sni", query.get("peer", [""]))[0]
        if sni:
            tls_settings["serverName"] = sni
        if query.get("allowInsecure", query.get("insecure", ["0"]))[0] in {"1", "true"}:
            tls_settings["allowInsecure"] = True
        stream["tlsSettings"] = tls_settings
    if stream["network"] == "ws":
        stream["wsSettings"] = {
            "path": query.get("path", ["/"])[0],
            "headers": {"Host": query.get("host", [""])[0]} if query.get("host", [""])[0] else {},
        }
    if security == "reality":
        stream["realitySettings"] = {
            "serverName": query.get("sni", [""])[0],
            "publicKey": query.get("pbk", [""])[0],
            "shortId": query.get("sid", [""])[0],
            "fingerprint": query.get("fp", ["chrome"])[0],
        }

    if scheme == "vless":
        if not user:
            return None
        outbound = {"protocol": "vless", "settings": {"vnext": [{"address": host, "port": port, "users": [{
            "id": user, "encryption": query.get("encryption", ["none"])[0], "flow": query.get("flow", [""])[0],
        }]}]}, "streamSettings": stream}
    elif scheme in {"ss", "shadowsocks"}:
        method, separator, password = user.partition(":")
        if not separator:
            try:
                method, password = normalize_base64(parsed.netloc.rsplit("@", 1)[0]).decode().split(":", 1)
            except (ValueError, UnicodeDecodeError):
                return None
        if not method or not password:
            return None
        outbound = {"protocol": "shadowsocks", "settings": {"servers": [{
            "address": host, "port": port, "method": method, "password": password,
        }]}}
    elif scheme == "trojan":
        if not user:
            return None
        outbound = {"protocol": "trojan", "settings": {"servers": [{"address": host, "port": port, "password": user}]}, "streamSettings": stream}
    elif scheme in {"hysteria2", "hy2"}:
        if not user:
            return None
        outbound = {"protocol": "hysteria2", "settings": {"servers": [{"address": host, "port": port, "password": user}]}, "streamSettings": stream}
    elif scheme == "tuic":
        if not user or not parsed.password:
            return None
        outbound = {"protocol": "tuic", "settings": {"servers": [{
            "address": host, "port": port, "uuid": user, "password": unquote(parsed.password),
            "congestion_control": query.get("congestion_control", ["bbr"])[0],
        }]}, "streamSettings": stream}
    else:
        return None
    return scheme, outbound


def find_xray_binary() -> str | None:
    configured = os.getenv("XRAY_BIN")
    if configured and os.path.isfile(configured) and os.access(configured, os.X_OK):
        return configured
    return shutil.which("xray")


async def wait_local_listener(port: int, process: subprocess.Popen[str], timeout: float) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if process.poll() is not None:
            return False
        try:
            _, writer, _ = await open_tcp("127.0.0.1", port, 0.25)
            await close_writer(writer)
            return True
        except (OSError, asyncio.TimeoutError):
            await asyncio.sleep(0.1)
    return False


async def check_xray_uri(uri: str, timeout: float) -> CheckResult:
    parsed = parse_xray_uri(uri)
    if not parsed:
        return CheckResult("invalid", "xray_config", None, "unsupported_or_invalid_uri")
    xray = find_xray_binary()
    if not xray:
        return CheckResult("checker_error", "xray_config", None, "xray_binary_not_found")
    protocol, outbound = parsed
    with tempfile.TemporaryDirectory(prefix="remainingconnections-xray-") as directory:
        port_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        port_socket.bind(("127.0.0.1", 0))
        local_port = port_socket.getsockname()[1]
        port_socket.close()
        config = {
            "log": {"loglevel": "warning"},
            "inbounds": [{"listen": "127.0.0.1", "port": local_port, "protocol": "socks", "settings": {"udp": False}}],
            "outbounds": [outbound, {"protocol": "freedom", "tag": "direct"}],
        }
        config_path = os.path.join(directory, "config.json")
        with open(config_path, "w", encoding="utf-8") as handle:
            json.dump(config, handle)
        process = subprocess.Popen([xray, "run", "-c", config_path], stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        try:
            if not await wait_local_listener(local_port, process, min(timeout, 4)):
                stderr = (process.stderr.read() if process.stderr else "")[:300]
                return CheckResult("invalid", "xray_start", None, "xray_start_failed", stderr)
            result = await check_socks5("127.0.0.1", local_port, timeout)
            result.verification = f"xray_{protocol}_{result.verification}"
            return result
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)


def parse_telegram_proxy_url(value: str) -> dict[str, Any] | None:
    parsed = urlparse(value.strip())
    scheme = parsed.scheme.lower()
    query = parse_qs(parsed.query, keep_blank_values=True)
    if scheme in {"tg", "http", "https"} and (scheme == "tg" or parsed.netloc.lower() == "t.me"):
        kind = (parsed.netloc if scheme == "tg" else parsed.path.strip("/")).lower()
        if kind not in {"proxy", "socks"}:
            return None
        host_port = parse_host_port(query.get("server", [None])[0], query.get("port", [None])[0])
        if not host_port:
            return None
        host, port = host_port
        secret = query.get("secret", [""])[0].lower()
        if kind == "proxy":
            if not re.fullmatch(r"(?:dd|ee)?[0-9a-f]{32,128}", secret):
                return None
            return {"protocol": "mtproto", "host": host, "port": port, "secret": secret}
        return {"protocol": "socks5", "host": host, "port": port}
    if scheme in {"socks5", "socks"}:
        host_port = parse_host_port(parsed.hostname, parsed.port)
        return {"protocol": "socks5", "host": host_port[0], "port": host_port[1]} if host_port else None
    if scheme in {"http", "https"}:
        host_port = parse_host_port(parsed.hostname, parsed.port)
        return {"protocol": "http", "host": host_port[0], "port": host_port[1]} if host_port else None
    return None


async def check_telegram_proxy(proxy: dict[str, Any], timeout: float) -> CheckResult:
    protocol = (proxy.get("protocol") or "").lower()
    host = proxy.get("host") or proxy.get("server")
    port = proxy.get("port")
    host_port = parse_host_port(host, port)
    if not host_port:
        return CheckResult("invalid", "input_validation", None, "invalid_host_or_port")
    host, port = host_port
    if not await resolve_host(host, port, timeout):
        return CheckResult("invalid", "dns", None, "dns_resolution_failed")
    if protocol == "socks5":
        return await check_socks5(host, port, timeout)
    if protocol in {"http", "https"}:
        return await check_http_proxy(host, port, timeout)
    if protocol == "mtproto":
        # MTProto's encrypted transport must be validated by a Telegram client. Xray does not
        # implement MTProto outbound, so never label a bare TCP socket as a working proxy.
        writer = None
        try:
            _, writer, latency = await open_tcp(host, port, timeout)
            return CheckResult("unverified", "mtproto_tcp_only", latency, "mtproto_protocol_client_required")
        except asyncio.TimeoutError:
            return CheckResult("timeout", "mtproto_tcp_only", None, "timeout")
        except OSError as exc:
            return CheckResult("connection_failed", "mtproto_tcp_only", None, type(exc).__name__)
        finally:
            await close_writer(writer)
    return CheckResult("invalid", "input_validation", None, "unsupported_protocol")