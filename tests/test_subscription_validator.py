#!/usr/bin/env python3
"""Tests for subscription_validator module."""

import base64
import json
import pytest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from subscription_validator import (
    validate_subscription_content,
    URI_PROTOCOLS,
)


class TestURIListValidation:
    """Test validation of plain URI list subscriptions."""
    
    def test_valid_vless_uri_list(self):
        content = """
vless://uuid@example.com:443?security=tls&type=tcp#node1
vless://uuid@example.org:443?security=tls&type=ws#node2
        """
        result = validate_subscription_content(content.strip())
        assert result["valid"]
        assert result["format"] == "uri_list"
        assert result["configs_count"] == 2
        assert "vless" in result["protocols"]
    
    def test_valid_vmess_uri_list(self):
        config = {
            "v": "2",
            "ps": "test",
            "add": "example.com",
            "port": "443",
            "id": "uuid",
            "aid": "0",
        }
        encoded = base64.b64encode(json.dumps(config).encode()).decode()
        content = f"vmess://{encoded}"
        
        result = validate_subscription_content(content)
        assert result["valid"]
        assert "vmess" in result["protocols"]
    
    def test_valid_mixed_protocols(self):
        content = """
vless://uuid@example.com:443#node1
trojan://password@example.org:443#node2
ss://method:password@example.net:8388#node3
        """
        result = validate_subscription_content(content.strip())
        assert result["valid"]
        assert result["configs_count"] == 3
        assert len(result["protocols"]) == 3
    
    def test_empty_content(self):
        result = validate_subscription_content("")
        assert not result["valid"]
        assert result["format"] == "empty"
        assert "empty_content" in result["errors"]
    
    def test_whitespace_only(self):
        result = validate_subscription_content("   \n\n   ")
        assert not result["valid"]
        assert result["format"] == "empty"


class TestBase64Subscriptions:
    """Test validation of base64-encoded subscriptions."""
    
    def test_valid_base64_uri_list(self):
        uris = "vless://uuid@example.com:443#node1\nvless://uuid@example.org:443#node2"
        encoded = base64.b64encode(uris.encode()).decode()
        
        result = validate_subscription_content(encoded)
        assert result["valid"]
        assert result["format"] == "base64_uri_list"
        assert result["configs_count"] == 2
    
    def test_base64_with_padding(self):
        uris = "vless://uuid@example.com:443#test"
        encoded = base64.b64encode(uris.encode()).decode()
        
        result = validate_subscription_content(encoded)
        assert result["valid"]
        assert result["format"] == "base64_uri_list"
    
    def test_base64_urlsafe(self):
        uris = "vless://uuid@example.com:443#test"
        encoded = base64.urlsafe_b64encode(uris.encode()).decode()
        
        result = validate_subscription_content(encoded)
        assert result["valid"]
    
    def test_invalid_base64(self):
        content = "this-is-not-base64-!!!"
        result = validate_subscription_content(content)
        # Should fall back to treating as plain text
        assert not result["valid"]


class TestYAMLSubscriptions:
    """Test validation of YAML-format subscriptions."""
    
    def test_valid_clash_yaml(self):
        content = """
proxies:
  - name: node1
    type: vless
    server: example.com
    port: 443
    uuid: test-uuid
    tls: true
  - name: node2
    type: trojan
    server: example.org
    port: 443
    password: test-password
        """
        result = validate_subscription_content(content, "config.yaml")
        assert result["valid"]
        assert result["format"] == "yaml"
        assert result["configs_count"] >= 2
    
    def test_valid_v2ray_yaml(self):
        content = """
outbounds:
  - protocol: vless
    settings:
      vnext:
        - address: example.com
          port: 443
          users:
            - id: uuid
        """
        result = validate_subscription_content(content, "config.yml")
        assert result["valid"]
        assert result["format"] == "yaml"
    
    def test_invalid_yaml_syntax(self):
        content = """
proxies:
  - name: broken
    type: vless
    : invalid syntax here
        """
        result = validate_subscription_content(content, "config.yaml")
        assert not result["valid"]
        assert any("parse_error" in err for err in result["errors"])


class TestJSONSubscriptions:
    """Test validation of JSON-format subscriptions."""
    
    def test_valid_singbox_json(self):
        content = json.dumps({
            "outbounds": [
                {
                    "type": "vless",
                    "server": "example.com",
                    "server_port": 443,
                    "uuid": "test-uuid"
                },
                {
                    "type": "trojan",
                    "server": "example.org",
                    "server_port": 443,
                    "password": "test-password"
                }
            ]
        })
        result = validate_subscription_content(content, "config.json")
        assert result["valid"]
        assert result["format"] == "json"
        assert result["configs_count"] >= 2
    
    def test_valid_v2ray_json(self):
        content = json.dumps({
            "outbounds": [
                {
                    "protocol": "vless",
                    "settings": {
                        "vnext": [{
                            "address": "example.com",
                            "port": 443
                        }]
                    }
                }
            ]
        })
        result = validate_subscription_content(content, "config.json")
        assert result["valid"]
        assert result["format"] == "json"
    
    def test_invalid_json_syntax(self):
        content = '{"outbounds": [broken json}'
        result = validate_subscription_content(content, "config.json")
        assert not result["valid"]
        assert any("parse_error" in err for err in result["errors"])


class TestProtocolDetection:
    """Test protocol detection and counting."""
    
    def test_protocol_counting(self):
        content = """
vless://uuid@example.com:443#node1
vless://uuid@example.org:443#node2
trojan://password@example.net:443#node3
ss://method:password@example.io:8388#node4
        """
        result = validate_subscription_content(content.strip())
        assert result["protocols"]["vless"] == 2
        assert result["protocols"]["trojan"] == 1
        assert "ss" in result["protocols"] or "shadowsocks" in result["protocols"]
    
    def test_unique_configs_count(self):
        content = """
vless://uuid@example.com:443#node1
vless://uuid@example.com:443#node1
vless://uuid@example.org:443#node2
        """
        result = validate_subscription_content(content.strip())
        assert result["unique_configs_count"] == 2
        assert result["configs_count"] == 2


class TestSupportedProtocols:
    """Test supported protocol list."""
    
    def test_all_major_protocols_supported(self):
        assert "vless" in URI_PROTOCOLS
        assert "vmess" in URI_PROTOCOLS
        assert "ss" in URI_PROTOCOLS
        assert "shadowsocks" in URI_PROTOCOLS
        assert "trojan" in URI_PROTOCOLS
        assert "hysteria2" in URI_PROTOCOLS
        assert "hy2" in URI_PROTOCOLS
        assert "tuic" in URI_PROTOCOLS
        assert "wireguard" in URI_PROTOCOLS
        assert "wg" in URI_PROTOCOLS


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_very_large_subscription(self):
        # Create a large subscription
        uris = [f"vless://uuid@example{i}.com:443#node{i}" for i in range(1000)]
        content = "\n".join(uris)
        
        result = validate_subscription_content(content)
        assert result["valid"]
        assert result["configs_count"] == 1000
    
    def test_mixed_line_endings(self):
        content = "vless://uuid@example.com:443#node1\r\nvless://uuid@example.org:443#node2\nvless://uuid@example.net:443#node3"
        result = validate_subscription_content(content)
        assert result["valid"]
        assert result["configs_count"] == 3
    
    def test_unicode_in_comments(self):
        content = "vless://uuid@example.com:443#测试节点"
        result = validate_subscription_content(content)
        assert result["valid"]
        assert result["configs_count"] == 1
    
    def test_empty_lines_and_whitespace(self):
        content = """

        vless://uuid@example.com:443#node1
        
        
        vless://uuid@example.org:443#node2
        
        """
        result = validate_subscription_content(content)
        assert result["valid"]
        assert result["configs_count"] == 2


def test_module_constants():
    """Test module-level constants."""
    from subscription_validator import MAX_TEXT_BYTES, BASE64_CANDIDATE_RE, URI_RE
    
    assert MAX_TEXT_BYTES == 10_000_000
    assert BASE64_CANDIDATE_RE is not None
    assert URI_RE is not None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])