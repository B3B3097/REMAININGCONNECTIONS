#!/usr/bin/env python3
"""Tests for strict_proxy_checker module."""

import asyncio
import pytest
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from strict_proxy_checker import (
    parse_xray_uri,
    is_valid_host,
    parse_host_port,
    normalize_base64,
    check_socks5,
    check_http_proxy,
    parse_telegram_proxy_url,
    CheckResult,
)


class TestHostValidation:
    """Test host and port validation."""
    
    def test_valid_ipv4(self):
        assert is_valid_host("192.168.1.1")
        assert is_valid_host("8.8.8.8")
        assert is_valid_host("255.255.255.255")
    
    def test_valid_ipv6(self):
        assert is_valid_host("[2001:db8::1]")
        assert is_valid_host("[::1]")
    
    def test_valid_domain(self):
        assert is_valid_host("example.com")
        assert is_valid_host("sub.example.com")
        assert is_valid_host("test-server.example.org")
    
    def test_invalid_host(self):
        assert not is_valid_host("")
        assert not is_valid_host("invalid..domain")
        assert not is_valid_host("spaces in name")
        assert not is_valid_host("-invalid.com")
    
    def test_parse_host_port_valid(self):
        assert parse_host_port("example.com", 443) == ("example.com", 443)
        assert parse_host_port("192.168.1.1", "8080") == ("192.168.1.1", 8080)
    
    def test_parse_host_port_invalid(self):
        assert parse_host_port("", 443) is None
        assert parse_host_port("example.com", 0) is None
        assert parse_host_port("example.com", 70000) is None
        assert parse_host_port("example.com", "invalid") is None


class TestBase64:
    """Test base64 utilities."""
    
    def test_normalize_base64_standard(self):
        data = b"hello world"
        import base64
        encoded = base64.b64encode(data).decode()
        assert normalize_base64(encoded) == data
    
    def test_normalize_base64_urlsafe(self):
        data = b"test data with special chars: +/"
        import base64
        encoded = base64.urlsafe_b64encode(data).decode()
        assert normalize_base64(encoded) == data
    
    def test_normalize_base64_no_padding(self):
        # Base64 without padding
        encoded = "SGVsbG8"  # "Hello" without padding
        result = normalize_base64(encoded)
        assert result == b"Hello"


class TestXrayURIParsing:
    """Test Xray URI parsing."""
    
    def test_parse_vless_uri(self):
        uri = "vless://uuid-test@example.com:443?security=tls&type=tcp#test"
        result = parse_xray_uri(uri)
        assert result is not None
        protocol, outbound = result
        assert protocol == "vless"
        assert outbound["protocol"] == "vless"
    
    def test_parse_vmess_uri(self):
        # VMess uses base64 JSON
        import base64
        import json
        config = {
            "v": "2",
            "ps": "test",
            "add": "example.com",
            "port": "443",
            "id": "uuid-test",
            "aid": "0",
            "net": "tcp",
            "type": "none",
            "tls": "tls",
        }
        encoded = base64.b64encode(json.dumps(config).encode()).decode()
        uri = f"vmess://{encoded}"
        result = parse_xray_uri(uri)
        assert result is not None
        protocol, outbound = result
        assert protocol == "vmess"
    
    def test_parse_shadowsocks_uri(self):
        uri = "ss://cmM0LW1kNTpwYXNzd29yZA==@example.com:8388#test"
        result = parse_xray_uri(uri)
        assert result is not None
        protocol, outbound = result
        assert protocol in ("ss", "shadowsocks")
    
    def test_parse_trojan_uri(self):
        uri = "trojan://password@example.com:443?security=tls&type=tcp#test"
        result = parse_xray_uri(uri)
        assert result is not None
        protocol, outbound = result
        assert protocol == "trojan"
    
    def test_parse_invalid_uri(self):
        assert parse_xray_uri("") is None
        assert parse_xray_uri("invalid://") is None
        assert parse_xray_uri("http://example.com") is None


class TestTelegramProxyParsing:
    """Test Telegram proxy URL parsing."""
    
    def test_parse_mtproto_tg_scheme(self):
        url = "tg://proxy?server=example.com&port=443&secret=dd1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"
        result = parse_telegram_proxy_url(url)
        assert result is not None
        assert result["protocol"] == "mtproto"
        assert result["host"] == "example.com"
        assert result["port"] == 443
    
    def test_parse_mtproto_https_scheme(self):
        url = "https://t.me/proxy?server=example.com&port=443&secret=dd1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"
        result = parse_telegram_proxy_url(url)
        assert result is not None
        assert result["protocol"] == "mtproto"
    
    def test_parse_socks5_tg_scheme(self):
        url = "tg://socks?server=example.com&port=1080"
        result = parse_telegram_proxy_url(url)
        assert result is not None
        assert result["protocol"] == "socks5"
        assert result["host"] == "example.com"
        assert result["port"] == 1080
    
    def test_parse_socks5_direct(self):
        url = "socks5://example.com:1080"
        result = parse_telegram_proxy_url(url)
        assert result is not None
        assert result["protocol"] == "socks5"
    
    def test_parse_http_proxy(self):
        url = "http://example.com:8080"
        result = parse_telegram_proxy_url(url)
        assert result is not None
        assert result["protocol"] == "http"
    
    def test_parse_invalid_proxy_url(self):
        assert parse_telegram_proxy_url("") is None
        assert parse_telegram_proxy_url("invalid") is None
        assert parse_telegram_proxy_url("tg://proxy?server=") is None


@pytest.mark.asyncio
class TestProxyChecks:
    """Test actual proxy checking (requires running proxies)."""
    
    async def test_check_result_dataclass(self):
        result = CheckResult(
            status="working",
            verification="test",
            latency_ms=100.5,
            error=None,
        )
        assert result.status == "working"
        assert result.latency_ms == 100.5
        
        result_dict = result.as_dict()
        assert result_dict["status"] == "working"
        assert result_dict["latency_ms"] == 100.5
    
    async def test_check_socks5_invalid_host(self):
        result = await check_socks5("invalid.local.test", 1080, timeout=2.0)
        assert result.status in ("timeout", "connection_failed", "invalid")
    
    async def test_check_http_proxy_invalid_host(self):
        result = await check_http_proxy("invalid.local.test", 8080, timeout=2.0)
        assert result.status in ("timeout", "connection_failed", "invalid")


class TestProtocolSupport:
    """Test protocol detection and support."""
    
    def test_supported_protocols(self):
        from strict_proxy_checker import SUPPORTED_XRAY_PROTOCOLS
        assert "vless" in SUPPORTED_XRAY_PROTOCOLS
        assert "vmess" in SUPPORTED_XRAY_PROTOCOLS
        assert "shadowsocks" in SUPPORTED_XRAY_PROTOCOLS
        assert "trojan" in SUPPORTED_XRAY_PROTOCOLS
        assert "hysteria2" in SUPPORTED_XRAY_PROTOCOLS
        assert "tuic" in SUPPORTED_XRAY_PROTOCOLS


def test_imports():
    """Test that all required functions are importable."""
    from strict_proxy_checker import (
        check_telegram_proxy,
        check_xray_uri,
        parse_xray_uri,
        utc_timestamp,
        find_xray_binary,
    )
    assert callable(check_telegram_proxy)
    assert callable(check_xray_uri)
    assert callable(parse_xray_uri)
    assert callable(utc_timestamp)
    assert callable(find_xray_binary)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])