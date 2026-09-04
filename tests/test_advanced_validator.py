#!/usr/bin/env python3
"""Tests for the Advanced Proxy Validator Engine."""

import asyncio
import hashlib
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure scripts directory is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from advanced_validator import (
    ValidationConfig, ValidationResult, HeaderInjector, 
    TLSFingerprintSimulator, DeepValidator, Protocol, ClientFingerprint
)


class TestHeaderInjector:
    """Test cases for HeaderInjector."""

    def test_generate_vmess_ws_header(self):
        headers = HeaderInjector.generate_vmess_ws_header("/ws", "example.com")
        assert "Host" in headers
        assert headers["Host"] == "example.com"
        assert "Upgrade" in headers
        assert "Sec-WebSocket-Key" in headers

    def test_generate_grpc_header(self):
        headers = HeaderInjector.generate_grpc_header("api.service", "authority.example.com")
        assert ":method" in headers
        assert headers[":method"] == "POST"
        assert "content-type" in headers

    def test_generate_http_upgrade_header(self):
        headers = HeaderInjector.generate_http_upgrade_header("cdn.example.com", "/path")
        assert headers["Connection"] == "Upgrade"
        assert "/path" in headers.get("Path", "")


class TestTLSFingerprintSimulator:
    """Test cases for TLS Fingerprint Simulation."""

    def test_build_client_hello(self):
        # Just checking it returns bytes and isn't empty
        hello = TLSFingerprintSimulator.build_client_hello(ClientFingerprint.CHROME_120, "example.com")
        assert isinstance(hello, bytes)
        assert len(hello) > 0

    def test_verify_server_response_valid(self):
        # Mock SSL record header
        valid_resp = b"\x16\x03\x03" + b"\x00\x00" * 10
        result = TLSFingerprintSimulator.verify_server_response(valid_resp, "example.com")
        assert result is True

    def test_verify_server_response_invalid(self):
        invalid_resp = b""
        result = TLSFingerprintSimulator.verify_server_response(invalid_resp, "example.com")
        assert result is False


class TestDeepValidator:
    """Test cases for the Main Validator Class."""

    @pytest.fixture
    def validator(self):
        return DeepValidator(concurrency=2, timeout=2.0)

    def test_validate_proxy_invalid_host(self, validator):
        """Validation should fail gracefully on invalid host."""
        config = ValidationConfig(
            target_host="invalid.host.test.local",
            target_port=443,
            protocol=Protocol.TROJAN
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(validator.validate_proxy(config))
            assert result.tcp_success is False
            assert result.score < 50.0
            assert "Error" in result.handshake_error or "Timeout" in result.handshake_error
        finally:
            loop.close()

    def test_calculate_score_extreme_latency(self):
        """Score should decrease with high latency."""
        result = ValidationResult(
            config_hash="abc",
            host="test",
            port=443,
            protocol="test",
            tcp_success=True,
            tcp_latency_ms=2000.0,
            tls_success=True,
            handshake_success=True
        )
        
        score = validator._calculate_score(result, elapsed_seconds=1.0)
        # High latency penalty
        assert score < 80.0

    def test_batch_validate_empty(self, validator):
        """Batch validation with empty list should return empty."""
        results = validator.batch_validate([])
        assert len(results) == 0


class TestValidationConfig:
    """Test cases for Configuration Data Classes."""

    def test_default_fingerprint(self):
        config = ValidationConfig(target_host="test", target_port=443, protocol=Protocol.HTTP)
        assert config.fingerprint == ClientFingerprint.CHROME_120

    def test_custom_headers(self):
        custom = {"X-Custom": "Value"}
        config = ValidationConfig(
            target_host="test", 
            target_port=443, 
            protocol=Protocol.VMESS,
            custom_headers=custom
        )
        assert config.custom_headers == custom