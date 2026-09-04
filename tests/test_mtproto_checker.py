#!/usr/bin/env python3
"""Tests for telegram_mtproto_checker module."""

import asyncio
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from telegram_mtproto_checker import (
    decode_mtproto_secret,
    generate_mtproto_handshake,
    check_mtproto_proxy_full,
    MTProtoCheckResult,
)


class TestSecretDecoding:
    """Test MTProto secret decoding."""
    
    def test_decode_valid_secret(self):
        secret = "dd1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"
        result = decode_mtproto_secret(secret)
        assert isinstance(result, bytes)
        assert len(result) >= 16
    
    def test_decode_secret_without_prefix(self):
        secret = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"
        result = decode_mtproto_secret(secret)
        assert isinstance(result, bytes)
    
    def test_decode_secret_with_ee_prefix(self):
        secret = "ee1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"
        result = decode_mtproto_secret(secret)
        assert isinstance(result, bytes)
    
    def test_decode_empty_secret(self):
        with pytest.raises(ValueError, match="Empty secret"):
            decode_mtproto_secret("")
    
    def test_decode_invalid_hex(self):
        with pytest.raises(ValueError, match="Invalid hex secret"):
            decode_mtproto_secret("gghhiijj")
    
    def test_decode_too_short(self):
        with pytest.raises(ValueError, match="Secret too short"):
            decode_mtproto_secret("dd123456")
    
    def test_decode_uppercase(self):
        secret = "DD1234567890ABCDEF1234567890ABCDEF1234567890ABCDEF1234567890ABCD"
        result = decode_mtproto_secret(secret)
        assert isinstance(result, bytes)


class TestHandshakeGeneration:
    """Test MTProto handshake generation."""
    
    def test_generate_handshake(self):
        secret = b"0" * 32
        packet, key = generate_mtproto_handshake(secret)
        
        assert isinstance(packet, bytes)
        assert isinstance(key, bytes)
        assert len(packet) >= 64
        assert len(key) == 32
    
    def test_handshake_randomness(self):
        secret = b"0" * 32
        packet1, key1 = generate_mtproto_handshake(secret)
        packet2, key2 = generate_mtproto_handshake(secret)
        
        # Different nonces should produce different packets
        assert packet1 != packet2
        assert key1 != key2


@pytest.mark.asyncio
class TestMTProtoChecks:
    """Test MTProto proxy checking."""
    
    async def test_check_result_dataclass(self):
        result = MTProtoCheckResult(
            status="working",
            verification="mtproto_handshake",
            latency_ms=150.0,
            error=None,
            protocol_version="mtproto",
        )
        assert result.status == "working"
        assert result.latency_ms == 150.0
        assert result.protocol_version == "mtproto"
    
    async def test_check_invalid_secret(self):
        result = await check_mtproto_proxy_full(
            host="example.com",
            port=443,
            secret="invalid",
            timeout=2.0,
        )
        assert result.status == "invalid"
        assert "invalid_secret" in (result.error or "")
    
    async def test_check_invalid_host(self):
        result = await check_mtproto_proxy_full(
            host="invalid.local.test.nonexistent",
            port=443,
            secret="dd1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
            timeout=2.0,
        )
        assert result.status in ("timeout", "connection_failed")
    
    async def test_check_with_valid_secret_format(self):
        # This will fail connection but secret should be valid
        result = await check_mtproto_proxy_full(
            host="127.0.0.1",
            port=9999,
            secret="dd1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd",
            timeout=1.0,
        )
        # Should not be invalid due to secret
        assert result.verification != "secret_validation"


class TestTelegramDCs:
    """Test Telegram DC configuration."""
    
    def test_dc_addresses_available(self):
        from telegram_mtproto_checker import TELEGRAM_DCS, CONTROL_DC
        
        assert len(TELEGRAM_DCS) > 0
        assert all(isinstance(dc, tuple) and len(dc) == 2 for dc in TELEGRAM_DCS)
        assert isinstance(CONTROL_DC, tuple)
        assert len(CONTROL_DC) == 2


class TestSecretFormats:
    """Test various MTProto secret formats."""
    
    def test_32_char_secret(self):
        secret = "1234567890abcdef1234567890abcdef"
        result = decode_mtproto_secret(secret)
        assert len(result) == 16
    
    def test_64_char_secret(self):
        secret = "1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef"
        result = decode_mtproto_secret(secret)
        assert len(result) == 32
    
    def test_dd_prefix_secret(self):
        secret = "dd1234567890abcdef1234567890abcdef"
        result = decode_mtproto_secret(secret)
        assert isinstance(result, bytes)
    
    def test_ee_prefix_secret(self):
        secret = "ee1234567890abcdef1234567890abcdef"
        result = decode_mtproto_secret(secret)
        assert isinstance(result, bytes)


def test_module_imports():
    """Test that all required components are importable."""
    from telegram_mtproto_checker import (
        check_mtproto_handshake,
        check_mtproto_dc_connectivity,
        batch_check_mtproto_proxies,
    )
    assert callable(check_mtproto_handshake)
    assert callable(check_mtproto_dc_connectivity)
    assert callable(batch_check_mtproto_proxies)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])