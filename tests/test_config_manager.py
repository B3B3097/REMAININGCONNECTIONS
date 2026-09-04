#!/usr/bin/env python3
"""Tests for the Configuration Manager module."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure scripts directory is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from config_manager import ConfigManager, SettingDefinition


class TestConfigManager:
    """Test cases for ConfigManager."""

    def setup_method(self):
        self.config = ConfigManager("TestApp")
        # Clear default settings for isolated tests if needed, 
        # but here we rely on the defaults registered in __init__

    def test_get_default_value(self):
        assert self.config.get("DEBUG") == False
        assert self.config.get("LOG_LEVEL") == "INFO"

    def test_set_and_get_value(self):
        self.config.set("DEBUG", True)
        assert self.config.get("DEBUG") is True

    def test_invalid_setting_type(self):
        with pytest.raises(ValueError):
            self.config.set("NETWORK_TIMEOUT", "not_a_number")

    def test_sensitive_data_masking(self):
        self.config.set("GITHUB_TOKEN", "secret_token_123")
        # Access internal settings dict directly to check value
        assert self.config.settings["GITHUB_TOKEN"] == "secret_token_123"
        
        # Check export method masks it
        exported = self.config.export_to_dict(mask_secrets=True)
        assert exported["GITHUB_TOKEN"] == "***MASKED***"
        
        # Unmasked export should have the real value
        unexported = self.config.export_to_dict(mask_secrets=False)
        assert unexported["GITHUB_TOKEN"] == "secret_token_123"

    def test_load_from_dict(self):
        self.config.load_from_dict({"DATA_DIR": "/custom/path"})
        assert self.config.get("DATA_DIR") == "/custom/path"

    def test_validate_missing_required(self):
        # Simulate removing a required setting
        original_val = self.config.settings.get("GITHUB_TOKEN")
        if original_val:
            del self.config.settings["GITHUB_TOKEN"]
            
        errors = self.config.validate()
        assert any("GITHUB_TOKEN" in e for e in errors)

    def test_export_json(self, tmp_path):
        output_file = tmp_path / "config.json"
        self.config.save_to_json(str(output_file))
        
        with open(output_file, 'r') as f:
            data = json.load(f)
        
        assert "APP_NAME" in data
        assert data["APP_NAME"] == "TestApp"


class TestSettingDefinition:
    """Test cases for SettingDefinition."""

    def test_cast_bool_string_true(self):
        sd = SettingDefinition("TEST", False, type_hint=bool)
        assert sd.cast_value("true") is True
        assert sd.cast_value("1") is True

    def test_cast_bool_string_false(self):
        sd = SettingDefinition("TEST", True, type_hint=bool)
        assert sd.cast_value("false") is False
        assert sd.cast_value("0") is False

    def test_cast_int(self):
        sd = SettingDefinition("PORT", 80, type_hint=int)
        assert sd.cast_value("8080") == 8080

    def test_cast_float(self):
        sd = SettingDefinition("TIMEOUT", 1.0, type_hint=float)
        assert sd.cast_value("5.5") == 5.5