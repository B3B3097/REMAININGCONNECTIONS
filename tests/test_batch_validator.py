#!/usr/bin/env python3
"""Tests for the Batch Validator module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure scripts directory is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from batch_validator import BatchProcessor


class TestBatchProcessor:
    """Test cases for BatchProcessor."""

    def setup_method(self):
        self.fixture_dir = Path("tests/fixtures/batch_test")
        self.fixture_dir.mkdir(parents=True, exist_ok=True)
        
        # Create dummy input data
        self.input_file = self.fixture_dir / "input.json"
        data = {
            "proxies": [
                {"server": "1.2.3.4", "port": 8080, "protocol": "vless", "secret": "uuid1"},
                {"server": "5.6.7.8", "port": 443, "protocol": "trojan", "secret": "pass1"}
            ]
        }
        self.input_file.write_text(json.dumps(data), encoding="utf-8")
        
        self.output_file = self.fixture_dir / "output.json"

    def teardown_method(self):
        import shutil
        if self.fixture_dir.exists():
            shutil.rmtree(self.fixture_dir)

    @patch('batch_validator.DeepValidator')
    def test_process_file_success(self, mock_validator_class, tmp_path):
        """Test successful validation and data update."""
        # Setup mock
        mock_instance = MagicMock()
        mock_validator_class.return_value = mock_instance
        
        # Mock the batch_validate return value
        from advanced_validator import ValidationResult
        res = ValidationResult(
            config_hash="abc",
            host="1.2.3.4",
            port=8080,
            protocol="vless",
            tcp_success=True,
            tcp_latency_ms=50.0,
            handshake_success=True,
            score=95.5
        )
        mock_instance.batch_validate.return_value = [res]
        
        processor = BatchProcessor(concurrency=1)
        
        # Use temp paths for this test
        in_f = tmp_path / "in.json"
        out_f = tmp_path / "out.json"
        in_f.write_text(json.dumps({"proxies": [{"server": "1.2.3.4", "port": 8080, "protocol": "vless", "secret": "u1"}]}))
        
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(processor.process_file(str(in_f), str(out_f)))
            
            # Check output
            with open(out_f) as f:
                result_data = json.load(f)
            
            assert len(result_data["proxies"]) == 1
            assert result_data["proxies"][0]["deep_score"] == 95.5
            assert result_data["proxies"][0]["status"] == "working"
        finally:
            loop.close()

    @patch('batch_validator.DeepValidator')
    def test_process_file_unsupported_protocol(self, mock_validator_class, tmp_path):
        """Test handling of unsupported protocols (e.g., socks5)."""
        mock_instance = MagicMock()
        mock_validator_class.return_value = mock_instance
        
        processor = BatchProcessor(concurrency=1)
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            in_f = tmp_path / "in.json"
            out_f = tmp_path / "out.json"
            # Socks5 is not mapped in batch_validator currently
            data = {"proxies": [{"server": "1.2.3.4", "port": 1080, "protocol": "socks5"}]}
            in_f.write_text(json.dumps(data))
            
            loop.run_until_complete(processor.process_file(str(in_f), str(out_f)))
            
            with open(out_f) as f:
                result_data = json.load(f)
            
            # Should be present but not validated deeply (skipped)
            assert len(result_data["proxies"]) == 1
            assert "deep_score" not in result_data["proxies"][0]
        finally:
            loop.close()