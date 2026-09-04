#!/usr/bin/env python3
"""Tests for config_exporter module."""

import json
import pytest
import yaml
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from config_exporter import ConfigExporter


class TestConfigExporter:
    """Test ConfigExporter class."""
    
    @pytest.fixture
    def sample_proxies(self):
        """Sample proxy data for testing."""
        return [
            {
                "protocol": "vless",
                "host": "example.com",
                "port": 443,
                "uuid": "test-uuid-1",
                "url": "vless://test-uuid-1@example.com:443?security=tls#node1",
            },
            {
                "protocol": "vmess",
                "host": "example.org",
                "port": 443,
                "uuid": "test-uuid-2",
                "url": "vmess://encoded-config#node2",
            },
            {
                "protocol": "shadowsocks",
                "host": "example.net",
                "port": 8388,
                "url": "ss://method:password@example.net:8388#node3",
            },
            {
                "protocol": "trojan",
                "host": "example.io",
                "port": 443,
                "secret": "password123",
                "url": "trojan://password123@example.io:443#node4",
            },
            {
                "protocol": "socks5",
                "host": "example.dev",
                "port": 1080,
                "url": "socks5://example.dev:1080",
            },
        ]
    
    def test_exporter_initialization(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        assert exporter.proxies == sample_proxies


class TestURIExport(TestConfigExporter):
    """Test URI list export."""
    
    def test_to_uri_list(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        uris = exporter.to_uri_list()
        
        assert len(uris) == 5
        assert all(isinstance(uri, str) for uri in uris)
        assert any("vless://" in uri for uri in uris)
        assert any("vmess://" in uri for uri in uris)
    
    def test_to_uri_list_empty(self):
        exporter = ConfigExporter([])
        uris = exporter.to_uri_list()
        assert len(uris) == 0
    
    def test_to_uri_list_missing_url(self):
        proxies = [{"protocol": "vless", "host": "example.com", "port": 443}]
        exporter = ConfigExporter(proxies)
        uris = exporter.to_uri_list()
        assert len(uris) == 0


class TestBase64Export(TestConfigExporter):
    """Test base64 subscription export."""
    
    def test_to_base64_subscription(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        base64_sub = exporter.to_base64_subscription()
        
        assert isinstance(base64_sub, str)
        assert len(base64_sub) > 0
        
        # Decode and verify
        import base64
        decoded = base64.b64decode(base64_sub).decode("utf-8")
        assert "vless://" in decoded
        assert "vmess://" in decoded
    
    def test_base64_roundtrip(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        base64_sub = exporter.to_base64_subscription()
        
        # Decode back
        import base64
        decoded = base64.b64decode(base64_sub).decode("utf-8")
        uris = decoded.split("\n")
        
        assert len(uris) == 5


class TestClashExport(TestConfigExporter):
    """Test Clash YAML export."""
    
    def test_to_clash_yaml(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        clash_yaml = exporter.to_clash_yaml()
        
        assert isinstance(clash_yaml, str)
        assert len(clash_yaml) > 0
        
        # Parse YAML
        config = yaml.safe_load(clash_yaml)
        assert "proxies" in config
        assert "proxy-groups" in config
        assert len(config["proxies"]) > 0
    
    def test_clash_proxy_structure(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        clash_yaml = exporter.to_clash_yaml()
        config = yaml.safe_load(clash_yaml)
        
        proxy = config["proxies"][0]
        assert "name" in proxy
        assert "type" in proxy
        assert "server" in proxy
        assert "port" in proxy
    
    def test_clash_proxy_group(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        clash_yaml = exporter.to_clash_yaml()
        config = yaml.safe_load(clash_yaml)
        
        assert len(config["proxy-groups"]) > 0
        group = config["proxy-groups"][0]
        assert group["name"] == "auto"
        assert group["type"] == "url-test"
        assert len(group["proxies"]) > 0


class TestV2RayExport(TestConfigExporter):
    """Test V2Ray JSON export."""
    
    def test_to_v2ray_json(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        v2ray_json = exporter.to_v2ray_json()
        
        assert isinstance(v2ray_json, str)
        
        # Parse JSON
        config = json.loads(v2ray_json)
        assert "log" in config
        assert "inbounds" in config
        assert "outbounds" in config
    
    def test_v2ray_outbounds(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        v2ray_json = exporter.to_v2ray_json()
        config = json.loads(v2ray_json)
        
        assert len(config["outbounds"]) > 1  # proxies + direct
        
        # Check protocol diversity
        protocols = {ob.get("protocol") for ob in config["outbounds"]}
        assert "vless" in protocols or "vmess" in protocols
    
    def test_v2ray_inbound(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        v2ray_json = exporter.to_v2ray_json()
        config = json.loads(v2ray_json)
        
        assert len(config["inbounds"]) > 0
        inbound = config["inbounds"][0]
        assert inbound["protocol"] == "socks"
        assert inbound["port"] == 1080


class TestSingBoxExport(TestConfigExporter):
    """Test sing-box JSON export."""
    
    def test_to_singbox_json(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        singbox_json = exporter.to_singbox_json()
        
        assert isinstance(singbox_json, str)
        
        # Parse JSON
        config = json.loads(singbox_json)
        assert "log" in config
        assert "inbounds" in config
        assert "outbounds" in config
    
    def test_singbox_outbound_structure(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        singbox_json = exporter.to_singbox_json()
        config = json.loads(singbox_json)
        
        outbound = config["outbounds"][0]
        assert "type" in outbound
        assert "tag" in outbound
        assert "server" in outbound
        assert "server_port" in outbound


class TestQuantumultXExport(TestConfigExporter):
    """Test QuantumultX export."""
    
    def test_to_quantumultx(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        qx_config = exporter.to_quantumultx()
        
        assert isinstance(qx_config, str)
        assert "[server_local]" in qx_config
        
        lines = qx_config.split("\n")
        # Filter out empty lines and headers
        config_lines = [l for l in lines if l.strip() and not l.startswith("[")]
        assert len(config_lines) > 0
    
    def test_quantumultx_format(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        qx_config = exporter.to_quantumultx()
        
        # Check for protocol-specific syntax
        lines = qx_config.split("\n")
        has_shadowsocks = any("shadowsocks=" in l for l in lines)
        has_trojan = any("trojan=" in l for l in lines)
        
        assert has_shadowsocks or has_trojan


class TestSurgeExport(TestConfigExporter):
    """Test Surge export."""
    
    def test_to_surge(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        surge_config = exporter.to_surge()
        
        assert isinstance(surge_config, str)
        assert "[Proxy]" in surge_config
        
        lines = surge_config.split("\n")
        config_lines = [l for l in lines if l.strip() and not l.startswith("[")]
        assert len(config_lines) > 0
    
    def test_surge_format(self, sample_proxies):
        exporter = ConfigExporter(sample_proxies)
        surge_config = exporter.to_surge()
        
        lines = surge_config.split("\n")
        # Check for valid Surge proxy syntax (name = type, host, port)
        proxy_lines = [l for l in lines if "=" in l and not l.startswith("[")]
        assert len(proxy_lines) > 0
        
        # Verify basic structure
        for line in proxy_lines:
            assert "=" in line
            parts = line.split("=")
            assert len(parts) == 2


class TestEdgeCases(TestConfigExporter):
    """Test edge cases and error handling."""
    
    def test_empty_proxy_list(self):
        exporter = ConfigExporter([])
        
        assert exporter.to_uri_list() == []
        assert len(exporter.to_base64_subscription()) > 0  # Empty but valid base64
        
        clash = yaml.safe_load(exporter.to_clash_yaml())
        assert len(clash["proxies"]) == 0
    
    def test_proxies_missing_fields(self):
        incomplete_proxies = [
            {"protocol": "vless"},  # Missing host, port
            {"host": "example.com"},  # Missing protocol, port
            {"port": 443},  # Missing protocol, host
        ]
        
        exporter = ConfigExporter(incomplete_proxies)
        
        # Should not crash, just skip invalid entries
        uris = exporter.to_uri_list()
        clash_yaml = exporter.to_clash_yaml()
        
        assert isinstance(uris, list)
        assert isinstance(clash_yaml, str)
    
    def test_unsupported_protocol(self):
        proxies = [
            {
                "protocol": "unknown_protocol",
                "host": "example.com",
                "port": 443,
                "url": "unknown://example.com:443",
            }
        ]
        
        exporter = ConfigExporter(proxies)
        
        # Should handle gracefully
        v2ray_json = exporter.to_v2ray_json()
        config = json.loads(v2ray_json)
        
        # Only direct outbound should be present
        assert len([ob for ob in config["outbounds"] if ob["protocol"] != "freedom"]) == 0


def test_module_imports():
    """Test that module can be imported."""
    from config_exporter import ConfigExporter
    assert ConfigExporter is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])