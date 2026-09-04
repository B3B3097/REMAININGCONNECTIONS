#!/usr/bin/env python3
"""Tests for the Data Processor module."""

import json
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Ensure scripts directory is in path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from data_processor import DataCleaner, FuzzyMatcher, ProxyScorer, DataMerger


class TestDataCleaner:
    """Test cases for DataCleaner."""

    def test_clean_url_valid(self):
        assert DataCleaner.clean_url("  https://example.com  ") == "https://example.com"

    def test_clean_url_invalid(self):
        assert DataCleaner.clean_url("ftp://example.com") is None

    def test_validate_proxy_missing_fields(self):
        assert not DataCleaner.validate_proxy({"server": "1.2.3.4"})

    def test_validate_proxy_valid(self):
        assert DataCleaner.validate_proxy({"server": "1.2.3.4", "port": 443})

    def test_remove_duplicates(self):
        proxies = [
            {"server": "a", "port": 1, "secret": "s"},
            {"server": "a", "port": 1, "secret": "s"}, # Duplicate
            {"server": "b", "port": 2, "secret": "s"}, # Unique
        ]
        unique = DataCleaner.remove_duplicates(proxies)
        assert len(unique) == 2


class TestFuzzyMatcher:
    """Test cases for FuzzyMatcher."""

    def test_calculate_similarity_identical(self):
        assert FuzzyMatcher.calculate_similarity("abc", "abc") == 1.0

    def test_calculate_similarity_empty(self):
        assert FuzzyMatcher.calculate_similarity("", "abc") == 0.0

    def test_find_near_duplicates(self):
        proxies = [
            {"server": "1.1.1.1", "port": 80},
            {"server": "1.1.1.2", "port": 80}, # Similar
            {"server": "9.9.9.9", "port": 80}, # Different
        ]
        groups = FuzzyMatcher.find_near_duplicates(proxies, threshold=0.8)
        # Should find one group containing indices 0 and 1
        assert len(groups) >= 1
        assert 0 in groups[0]
        assert 1 in groups[0]


class TestProxyScorer:
    """Test cases for ProxyScorer."""

    def test_score_working_low_latency(self):
        proxy = {
            "status": "working",
            "latency_ms": 50,
            "sources": [{"repo": "r1"}],
            "protocol": "vless"
        }
        score = ProxyScorer.score(proxy)
        assert score > 80 # Should be high

    def test_score_failed_high_latency(self):
        proxy = {
            "status": "failed",
            "latency_ms": 5000,
            "sources": [],
            "protocol": "http"
        }
        score = ProxyScorer.score(proxy)
        assert score < 20 # Should be low

    def test_sort_proxies(self):
        proxies = [
            {"status": "failed", "latency_ms": 1000, "sources": [], "protocol": "http"},
            {"status": "working", "latency_ms": 100, "sources": [{"r": "1"}], "protocol": "vless"},
        ]
        sorted_p = ProxyScorer.sort_proxies(proxies)
        assert sorted_p[0]["status"] == "working"


class TestDataMerger:
    """Test cases for DataMerger."""

    def test_load_json_not_found(self, tmp_path):
        merger = DataMerger(data_dir=str(tmp_path))
        assert merger.load_json("nonexistent.json") is None

    def test_load_json_list_format(self, tmp_path):
        data = [{"id": 1}]
        f = tmp_path / "test.json"
        f.write_text(json.dumps(data), encoding="utf-8")
        
        merger = DataMerger(data_dir=str(tmp_path))
        result = merger.load_json("test.json")
        assert result == [{"id": 1}]

    def test_merge_all_creates_file(self, tmp_path):
        # Create dummy source files
        sub_data = {"proxies": [{"status": "working"}]}
        prox_data = {"proxies": [{"status": "working"}]}
        
        (tmp_path / "subscriptions_found.json").write_text(json.dumps(sub_data))
        (tmp_path / "tg_proxies_found.json").write_text(json.dumps(prox_data))
        
        merger = DataMerger(data_dir=str(tmp_path))
        result = merger.merge_all(output_file="merged_test.json")
        
        assert (tmp_path / "merged_test.json").exists()
        assert "subscriptions" in result
        assert "proxies" in result