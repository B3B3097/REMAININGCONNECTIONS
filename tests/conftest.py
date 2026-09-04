#!/usr/bin/env python3
"""Shared pytest fixtures and configuration for all tests."""

import asyncio
import json
import pytest
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


@pytest.fixture
def sample_vless_uri():
    """Sample VLESS URI for testing."""
    return "vless://12345678-1234-1234-1234-123456789abc@example.com:443?security=tls&type=tcp&headerType=none#TestNode"


@pytest.fixture
def sample_vmess_config():
    """Sample VMess configuration dictionary."""
    return {
        "v": "2",
        "ps": "TestNode",
        "add": "example.com",
        "port": "443",
        "id": "12345678-1234-1234-1234-123456789abc",
        "aid": "0",
        "net": "tcp",
        "type": "none",
        "host": "",
        "path": "",
        "tls": "tls",
        "sni": "example.com",
    }


@pytest.fixture
def sample_shadowsocks_uri():
    """Sample Shadowsocks URI for testing."""
    return "ss://Y2hhY2hhMjAtaWV0Zi1wb2x5MTMwNTpwYXNzd29yZA==@example.com:8388#TestNode"


@pytest.fixture
def sample_trojan_uri():
    """Sample Trojan URI for testing."""
    return "trojan://password123@example.com:443?security=tls&type=tcp#TestNode"


@pytest.fixture
def sample_mtproto_secret():
    """Sample MTProto secret for testing."""
    return "dd1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcd"


@pytest.fixture
def sample_proxy_list():
    """Sample list of proxies for testing."""
    return [
        {
            "id": 1,
            "protocol": "vless",
            "host": "example.com",
            "port": 443,
            "status": "working",
            "latency_ms": 120.5,
            "url": "vless://uuid@example.com:443#node1",
        },
        {
            "id": 2,
            "protocol": "vmess",
            "host": "example.org",
            "port": 443,
            "status": "working",
            "latency_ms": 150.2,
            "url": "vmess://config#node2",
        },
        {
            "id": 3,
            "protocol": "shadowsocks",
            "host": "example.net",
            "port": 8388,
            "status": "timeout",
            "latency_ms": None,
            "url": "ss://method:pass@example.net:8388#node3",
        },
        {
            "id": 4,
            "protocol": "trojan",
            "host": "example.io",
            "port": 443,
            "status": "working",
            "latency_ms": 95.8,
            "secret": "password",
            "url": "trojan://password@example.io:443#node4",
        },
        {
            "id": 5,
            "protocol": "socks5",
            "host": "example.dev",
            "port": 1080,
            "status": "invalid",
            "latency_ms": None,
        },
    ]


@pytest.fixture
def sample_subscription_content():
    """Sample subscription content for testing."""
    return """
vless://uuid1@server1.example.com:443?security=tls&type=tcp#Node1
vless://uuid2@server2.example.com:443?security=tls&type=ws&path=/ws#Node2
vmess://base64encodedconfig1#Node3
trojan://password1@server3.example.com:443?security=tls#Node4
ss://method:password@server4.example.com:8388#Node5
    """.strip()


@pytest.fixture
def sample_subscription_yaml():
    """Sample Clash YAML subscription."""
    return """
proxies:
  - name: Node1
    type: vless
    server: example.com
    port: 443
    uuid: 12345678-1234-1234-1234-123456789abc
    tls: true
  - name: Node2
    type: trojan
    server: example.org
    port: 443
    password: password123
    sni: example.org
    """.strip()


@pytest.fixture
def sample_subscription_json():
    """Sample V2Ray JSON subscription."""
    return json.dumps({
        "outbounds": [
            {
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": "example.com",
                        "port": 443,
                        "users": [{"id": "uuid", "encryption": "none"}]
                    }]
                }
            },
            {
                "protocol": "vmess",
                "settings": {
                    "vnext": [{
                        "address": "example.org",
                        "port": 443,
                        "users": [{"id": "uuid", "alterId": 0}]
                    }]
                }
            }
        ]
    })


@pytest.fixture
def temp_json_file(tmp_path):
    """Create a temporary JSON file."""
    def _create_file(data):
        file_path = tmp_path / "test_data.json"
        file_path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return file_path
    return _create_file


@pytest.fixture
def temp_text_file(tmp_path):
    """Create a temporary text file."""
    def _create_file(content):
        file_path = tmp_path / "test_data.txt"
        file_path.write_text(content, encoding="utf-8")
        return file_path
    return _create_file


@pytest.fixture
def mock_xray_binary(tmp_path, monkeypatch):
    """Mock Xray binary for testing."""
    xray_dir = tmp_path / "xray"
    xray_dir.mkdir()
    xray_binary = xray_dir / "xray"
    xray_binary.write_text("#!/bin/bash\necho 'Xray 1.8.0 (Mock)'", encoding="utf-8")
    xray_binary.chmod(0o755)
    
    monkeypatch.setenv("XRAY_BIN", str(xray_binary))
    return xray_binary


@pytest.fixture
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def async_client_session():
    """Provide an aiohttp ClientSession for async tests."""
    import aiohttp
    async with aiohttp.ClientSession() as session:
        yield session


@pytest.fixture
def mock_subprocess_run(monkeypatch):
    """Mock subprocess.run for testing."""
    mock = MagicMock()
    mock.return_value = MagicMock(
        returncode=0,
        stdout="Xray 1.8.0 (Mock)\n",
        stderr=""
    )
    monkeypatch.setattr("subprocess.run", mock)
    return mock


@pytest.fixture
def mock_requests_get(monkeypatch):
    """Mock requests.get for testing."""
    class MockResponse:
        def __init__(self, status_code=200, text="", json_data=None):
            self.status_code = status_code
            self.text = text
            self._json_data = json_data
        
        def json(self):
            return self._json_data or {}
        
        def raise_for_status(self):
            if self.status_code >= 400:
                raise Exception(f"HTTP {self.status_code}")
    
    mock = MagicMock()
    mock.return_value = MockResponse()
    monkeypatch.setattr("requests.get", mock)
    return mock


@pytest.fixture
def sample_xray_config():
    """Sample Xray configuration for testing."""
    return {
        "log": {"loglevel": "warning"},
        "inbounds": [{
            "listen": "127.0.0.1",
            "port": 10808,
            "protocol": "socks",
            "settings": {"udp": False}
        }],
        "outbounds": [
            {
                "protocol": "vless",
                "settings": {
                    "vnext": [{
                        "address": "example.com",
                        "port": 443,
                        "users": [{"id": "uuid", "encryption": "none"}]
                    }]
                },
                "streamSettings": {
                    "network": "tcp",
                    "security": "tls"
                }
            },
            {
                "protocol": "freedom",
                "tag": "direct"
            }
        ]
    }


@pytest.fixture
def sample_check_result():
    """Sample CheckResult for testing."""
    from strict_proxy_checker import CheckResult
    return CheckResult(
        status="working",
        verification="socks5_connect",
        latency_ms=120.5,
        error=None,
    )


@pytest.fixture
def sample_mtproto_check_result():
    """Sample MTProtoCheckResult for testing."""
    from telegram_mtproto_checker import MTProtoCheckResult
    return MTProtoCheckResult(
        status="working",
        verification="mtproto_handshake",
        latency_ms=150.0,
        error=None,
        protocol_version="mtproto",
    )


def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "network: marks tests that require network access"
    )
    config.addinivalue_line(
        "markers", "integration: marks integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_xray: marks tests that require Xray binary"
    )
    config.addinivalue_line(
        "markers", "requires_proxy: marks tests that require a running proxy"
    )


def pytest_collection_modifyitems(config, items):
    """Modify test collection to add markers automatically."""
    for item in items:
        # Mark async tests
        if asyncio.iscoroutinefunction(item.function):
            item.add_marker(pytest.mark.asyncio)
        
        # Mark network tests based on function name
        if "network" in item.nodeid.lower() or "api" in item.nodeid.lower():
            item.add_marker(pytest.mark.network)
        
        # Mark slow tests
        if "slow" in item.nodeid.lower():
            item.add_marker(pytest.mark.slow)


@pytest.fixture(autouse=True)
def reset_environment(monkeypatch):
    """Reset environment variables for each test."""
    # Clear relevant environment variables
    for key in list(monkeypatch._setitem):
        if key.startswith(("XRAY_", "PROXY_", "CHECK_", "MAX_")):
            monkeypatch.delenv(key, raising=False)