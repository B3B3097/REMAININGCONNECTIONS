#!/usr/bin/env python3
"""Tests for the Dashboard Generator module."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure scripts directory is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from dashboard_generator import DashboardGenerator


class TestDashboardGenerator:
    """Test cases for DashboardGenerator."""

    def setup_method(self):
        self.data_dir = Path("tests") / "fixtures" / "data"
        self.output_dir = Path("tests") / "fixtures" / "output"
        
        # Ensure directories exist for testing
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dummy data files
        self.proxies_file = self.data_dir / "tg_proxies_found.json"
        self.subs_file = self.data_dir / "subscriptions_found.json"
        
        proxies_data = {
            "proxies": [
                {"server": "1.2.3.4", "port": 8080, "protocol": "vless", "status": "working"},
                {"server": "5.6.7.8", "port": 443, "protocol": "trojan", "status": "failed"}
            ]
        }
        subs_data = {
            "subscriptions": [
                {"name": "sub1", "url": "http://example.com/sub"}
            ]
        }
        
        with open(self.proxies_file, 'w') as f:
            json.dump(proxies_data, f)
        with open(self.subs_file, 'w') as f:
            json.dump(subs_data, f)
            
        self.generator = DashboardGenerator(data_dir=str(self.data_dir), output_dir=str(self.output_dir))

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        if self.data_dir.exists():
            shutil.rmtree(self.data_dir)
        if self.output_dir.exists():
            shutil.rmtree(self.output_dir)

    def test_load_data(self):
        data = self.generator.load_data()
        assert len(data["proxies"]) == 2
        assert len(data["subscriptions"]) == 1
        assert "build_info" in data

    def test_generate_html_content(self):
        config_data = self.generator.load_data()
        html = self.generator.generate_html(config_data)
        
        # Check basic HTML structure
        assert "<!DOCTYPE html>" in html
        assert "REMAININGCONNECTIONS Dashboard" in html
        
        # Check if data is injected (simple string check)
        # Note: JSON keys might be escaped, so check for raw values
        assert "1.2.3.4" in html
        assert "vless" in html

    def test_output_file_creation(self):
        self.generator.run()
        output_file = self.output_dir / "index.html"
        assert output_file.exists()
        
        with open(output_file, 'r') as f:
            content = f.read()
        assert "1.2.3.4" in content

    def test_missing_data_files(self):
        # Remove one file
        self.proxies_file.unlink()
        
        generator = DashboardGenerator(data_dir=str(self.data_dir), output_dir=str(self.output_dir))
        data = generator.load_data()
        
        assert len(data["proxies"]) == 0
        assert len(data["subscriptions"]) == 1