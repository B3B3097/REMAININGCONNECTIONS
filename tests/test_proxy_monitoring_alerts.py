#!/usr/bin/env python3
"""Tests for the Proxy Health Monitor."""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

# Ensure scripts directory is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from proxy_monitoring_alerts import ProxyHealthMonitor


class TestProxyHealthMonitor:
    """Test cases for ProxyHealthMonitor."""

    @pytest.fixture
    def monitor(self, tmp_path):
        """Create a monitor instance with temporary directories."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()
        return ProxyHealthMonitor(data_dir=str(data_dir))

    def test_get_latest_proxy_file_no_data(self, monitor):
        """Should return None if no data files exist."""
        assert monitor.get_latest_proxy_file() is None

    def test_get_latest_proxy_file_with_data(self, monitor):
        """Should return the most recent file."""
        f1 = monitor.data_dir / "test1.json"
        f1.write_text("{}", encoding="utf-8")
        
        import time
        time.sleep(0.1)
        
        f2 = monitor.data_dir / "test2.json"
        f2.write_text("{}", encoding="utf-8")
        
        result = monitor.get_latest_proxy_file()
        assert result == f2

    def test_load_proxy_data(self, monitor):
        """Test loading valid JSON."""
        data = {"proxies": [{"status": "working", "protocol": "socks5"}]}
        f = monitor.data_dir / "proxies.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        
        loaded = monitor.load_proxy_data(f)
        assert len(loaded) == 1
        assert loaded[0]["status"] == "working"

    def test_analyze_health(self, monitor):
        """Analyze health metrics calculation."""
        proxies = [
            {"status": "working", "latency_ms": 100, "protocol": "socks5"},
            {"status": "working", "latency_ms": 200, "protocol": "mtproto"},
            {"status": "failed", "latency_ms": None, "protocol": "http"},
        ]
        
        metrics = monitor.analyze_health(proxies)
        
        assert metrics["total_proxies"] == 3
        assert metrics["working_count"] == 2
        assert metrics["failed_count"] == 1
        assert metrics["success_rate"] == pytest.approx(0.6666, rel=0.01)
        assert metrics["avg_latency_ms"] == pytest.approx(150.0)
        assert metrics["protocol_distribution"]["socks5"] == 1
        assert metrics["protocol_distribution"]["mtproto"] == 1

    def test_check_thresholds_low_success(self, monitor):
        """Alert triggered when success rate is too low."""
        metrics = {
            "total_proxies": 100,
            "working_count": 5,
            "failed_count": 95,
            "success_rate": 0.05,  # 5% < 10% threshold
            "avg_latency_ms": 100,
        }
        
        alerts = monitor.check_thresholds(metrics)
        
        assert any("CRITICAL" in a for a in alerts)
        assert any("Success rate" in a for a in alerts)

    def test_check_thresholds_high_latency(self, monitor):
        """Alert triggered when latency is high."""
        metrics = {
            "total_proxies": 100,
            "working_count": 90,
            "failed_count": 10,
            "success_rate": 0.9,
            "avg_latency_ms": 3000,  # > 2000ms threshold
        }
        
        alerts = monitor.check_thresholds(metrics)
        
        assert any("WARNING" in a for a in alerts)
        assert any("latency" in a.lower() for a in alerts)

    def test_check_thresholds_normal(self, monitor):
        """No alerts for normal metrics."""
        metrics = {
            "total_proxies": 100,
            "working_count": 80,
            "failed_count": 20,
            "success_rate": 0.8,
            "avg_latency_ms": 100,
        }
        
        alerts = monitor.check_thresholds(metrics)
        
        # Should only be info level or empty regarding critical warnings
        critical_or_warn = [a for a in alerts if "CRITICAL" in a or "WARNING" in a]
        assert len(critical_or_warn) == 0

    def test_save_metrics(self, monitor):
        """Test saving metrics to history file."""
        metrics = {"timestamp": "2023-01-01T00:00:00", "val": 1}
        
        monitor.save_metrics(metrics)
        
        assert monitor.metrics_path.exists()
        with open(monitor.metrics_path, 'r') as f:
            history = json.load(f)
        
        assert len(history) == 1
        assert history[0]["val"] == 1

    def test_run_check_no_data(self, monitor, caplog):
        """Run check should handle missing data gracefully."""
        # No data files created
        monitor.run_check()
        assert "No proxy data file found" in caplog.text