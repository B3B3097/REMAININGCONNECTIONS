#!/usr/bin/env python3
"""Advanced Data Processor for REMAININGCONNECTIONS.

This module handles complex data manipulation tasks including:
- Merging multiple JSON data sources (subscriptions, proxies, utils)
- Deduplication based on fuzzy matching
- Scoring and ranking proxies based on multiple metrics
- Generating statistical summaries and reports
- Cleaning malformed entries
- Exporting processed data to various formats
"""

import json
import os
import sys
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, Set
from collections import defaultdict
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("DataProcessor")


class DataCleaner:
    """Handles cleaning and validation of raw proxy/sub data."""

    @staticmethod
    def clean_url(url: str) -> Optional[str]:
        """Standardize URL format."""
        if not url or not isinstance(url, str):
            return None
        
        url = url.strip()
        
        # Remove trailing slashes
        url = url.rstrip('/')
        
        # Ensure protocol
        if not url.startswith(('http://', 'https://', 'socks://', 'socks5://', 'tg://')):
            # Attempt to guess
            if url.startswith('t.me'):
                url = url.replace('t.me', 'tg://')
            else:
                return None
                
        return url

    @staticmethod
    def validate_proxy(proxy: Dict[str, Any]) -> bool:
        """Check if a proxy entry has required fields."""
        required = ['server', 'port']
        for field in required:
            if field not in proxy:
                return False
        
        try:
            port = int(proxy['port'])
            if port < 1 or port > 65535:
                return False
        except (ValueError, TypeError):
            return False
            
        return True

    @staticmethod
    def remove_duplicates(proxies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Remove exact duplicates based on server:port:secret."""
        seen = set()
        unique = []
        
        for p in proxies:
            key_parts = [
                p.get('server', '').lower(),
                str(p.get('port', '')),
                p.get('secret', '').lower()
            ]
            key = tuple(key_parts)
            
            if key not in seen:
                seen.add(key)
                unique.append(p)
                
        return unique


class FuzzyMatcher:
    """Performs fuzzy matching for near-duplicate detection."""

    @staticmethod
    def calculate_similarity(s1: str, s2: str) -> float:
        """Simple Levenshtein distance based similarity."""
        if not s1 or not s2:
            return 0.0
        
        if s1 == s2:
            return 1.0
            
        len1, len2 = len(s1), len(s2)
        if len1 == 0 or len2 == 0:
            return 0.0
            
        # Dynamic programming approach for Levenshtein distance
        dp = [[0] * (len2 + 1) for _ in range(len1 + 1)]
        
        for i in range(len1 + 1):
            dp[i][0] = i
        for j in range(len2 + 1):
            dp[0][j] = j
            
        for i in range(1, len1 + 1):
            for j in range(1, len2 + 1):
                cost = 0 if s1[i-1] == s2[j-1] else 1
                dp[i][j] = min(
                    dp[i-1][j] + 1,      # deletion
                    dp[i][j-1] + 1,      # insertion
                    dp[i-1][j-1] + cost  # substitution
                )
                
        distance = dp[len1][len2]
        max_len = max(len1, len2)
        return 1.0 - (distance / max_len)

    @staticmethod
    def find_near_duplicates(proxies: List[Dict[str, Any]], threshold: float = 0.8) -> List[List[int]]:
        """Find groups of proxies that look similar but aren't identical."""
        n = len(proxies)
        groups = []
        visited = set()
        
        for i in range(n):
            if i in visited:
                continue
                
            group = [i]
            current_key = f"{proxies[i].get('server')}:{proxies[i].get('port')}"
            
            for j in range(i + 1, n):
                if j in visited:
                    continue
                    
                other_key = f"{proxies[j].get('server')}:{proxies[j].get('port')}"
                
                # Check similarity of keys
                sim = FuzzyMatcher.calculate_similarity(current_key.lower(), other_key.lower())
                
                if sim >= threshold:
                    group.append(j)
                    
            if len(group) > 1:
                groups.append(group)
                for idx in group:
                    visited.add(idx)
                    
        return groups


class ProxyScorer:
    """Ranks proxies based on various metrics."""

    WEIGHTS = {
        'status': 0.4,       # Working vs Failed
        'latency': 0.3,      # Speed matters
        'sources': 0.2,      # Popularity/Reliability
        'protocol': 0.1      # Protocol preference
    }

    PROTOCOL_PREF = {
        'vless': 10,
        'vmess': 9,
        'trojan': 8,
        'hysteria2': 7,
        'tuic': 7,
        'wg': 6,
        'ss': 5,
        'mtproto': 4,
        'socks5': 3,
        'http': 2
    }

    @classmethod
    def score(cls, proxy: Dict[str, Any]) -> float:
        """Calculate a composite score for a single proxy."""
        total_score = 0.0
        
        # Status Score (0-100)
        status = proxy.get('status', 'unknown').lower()
        if status == 'working':
            status_score = 100
        elif status == 'unverified':
            status_score = 50
        else:
            status_score = 0
        total_score += status_score * cls.WEIGHTS['status']
        
        # Latency Score (0-100)
        latency = proxy.get('latency_ms')
        if latency is not None:
            # Logarithmic decay: 100ms=100, 1000ms=50, 5000ms=10
            if latency <= 100:
                lat_score = 100
            elif latency >= 5000:
                lat_score = 10
            else:
                lat_score = 100 - ((latency - 100) / 4900) * 90
        else:
            lat_score = 50 # Neutral
        total_score += lat_score * cls.WEIGHTS['latency']
        
        # Sources Score (0-100)
        sources = proxy.get('sources', [])
        source_count = len(sources)
        src_score = min(100, source_count * 20) # Cap at 5 sources
        total_score += src_score * cls.WEIGHTS['sources']
        
        # Protocol Score
        proto = proxy.get('protocol', 'unknown').lower()
        proto_val = cls.PROTOCOL_PREF.get(proto, 1)
        proto_score = (proto_val / 10) * 100
        total_score += proto_score * cls.WEIGHTS['protocol']
        
        return round(total_score, 2)

    @classmethod
    def sort_proxies(cls, proxies: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Sort list of proxies by score descending."""
        return sorted(proxies, key=lambda p: cls.score(p), reverse=True)


class DataMerger:
    """Merges multiple JSON datasets."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)

    def load_json(self, filename: str) -> Optional[List[Dict[str, Any]]]:
        """Load a JSON file from data directory."""
        filepath = self.data_dir / filename
        if not filepath.exists():
            logger.warning(f"File not found: {filepath}")
            return None
            
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle wrapper objects like {"proxies": [...]}
            if isinstance(data, dict):
                return data.get('proxies', [])
            elif isinstance(data, list):
                return data
            else:
                return []
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")
            return None

    def merge_all(self, output_file: str = "merged_all.json") -> Dict[str, Any]:
        """Merge subscriptions, proxies, and utils into one file."""
        logger.info("Starting data merge...")
        
        merged_data = {
            "generated_at": datetime.utcnow().isoformat(),
            "source_files": [],
            "subscriptions": [],
            "proxies": [],
            "utils": []
        }
        
        # 1. Load Subscriptions
        sub_file = self.data_dir / "subscriptions_found.json"
        if sub_file.exists():
            subs = self.load_json("subscriptions_found.json")
            if subs:
                merged_data["subscriptions"] = subs
                merged_data["source_files"].append(str(sub_file))
                logger.info(f"Merged {len(subs)} subscriptions")
        
        # 2. Load Proxies
        prox_file = self.data_dir / "tg_proxies_found.json"
        if prox_file.exists():
            prox = self.load_json("tg_proxies_found.json")
            if prox:
                merged_data["proxies"] = prox
                merged_data["source_files"].append(str(prox_file))
                logger.info(f"Merged {len(prox)} proxies")
                
        # 3. Load Utils
        util_file = self.data_dir / "utils_found.json"
        if util_file.exists():
            utils = self.load_json("utils_found.json")
            if utils:
                merged_data["utils"] = utils
                merged_data["source_files"].append(str(util_file))
                logger.info(f"Merged {len(utils)} utils")
        
        # Save
        out_path = self.data_dir / output_file
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(merged_data, f, ensure_ascii=False, indent=2)
            
        logger.info(f"Merged data saved to {out_path}")
        return merged_data


class ReportGenerator:
    """Generates text-based reports from data."""

    @staticmethod
    def generate_summary(data: Dict[str, Any]) -> str:
        """Create a human-readable summary string."""
        lines = [
            "="*50,
            "REMAININGCONNECTIONS DATA REPORT",
            f"Generated: {data.get('generated_at', 'N/A')}",
            "="*50,
            ""
        ]
        
        subs = data.get("subscriptions", [])
        lines.append(f"Subscriptions: {len(subs)}")
        if subs:
            working = sum(1 for s in subs if s.get("status") == "working")
            lines.append(f"  - Working: {working}")
            lines.append(f"  - Offline: {len(subs) - working}")
            
        lines.append("")
        
        proxs = data.get("proxies", [])
        lines.append(f"Proxies: {len(proxs)}")
        if proxs:
            protocols = defaultdict(int)
            for p in proxs:
                protocols[p.get("protocol", "unknown")] += 1
            
            for proto, count in protocols.items():
                lines.append(f"  - {proto}: {count}")
                
        lines.append("")
        lines.append("="*50)
        
        return "\n".join(lines)

    @staticmethod
    def save_report(report_text: str, filename: str = "report.txt"):
        """Save report to file."""
        with open(filename, 'w', encoding='utf-8') as f:
            f.write(report_text)
        logger.info(f"Report saved to {filename}")


def main():
    """Main execution flow."""
    print("Initializing Data Processor...")
    
    cleaner = DataCleaner()
    scorer = ProxyScorer
    merger = DataMerger()
    reporter = ReportGenerator
    
    # 1. Merge Data
    merged = merger.merge_all()
    
    if not merged:
        print("No data to process.")
        return

    # 2. Clean & Deduplicate Proxies
    if merged["proxies"]:
        print("Cleaning proxies...")
        valid_proxies = [p for p in merged["proxies"] if cleaner.validate_proxy(p)]
        unique_proxies = cleaner.remove_duplicates(valid_proxies)
        print(f"Valid: {len(valid_proxies)}, Unique: {len(unique_proxies)}")
        
        # Sort by quality
        ranked_proxies = scorer.sort_proxies(unique_proxies)
        
        # Save ranked list
        output = {
            "generated_at": merged["generated_at"],
            "total": len(ranked_proxies),
            "proxies": ranked_proxies
        }
        
        ranked_path = Path("data") / "ranked_proxies.json"
        ranked_path.parent.mkdir(parents=True, exist_ok=True)
        with open(ranked_path, 'w', encoding='utf-8') as f:
            json.dump(output, f, ensure_ascii=False, indent=2)
        print(f"Saved ranked proxies to {ranked_path}")

    # 3. Generate Report
    report = reporter.generate_summary(merged)
    print(report)
    reporter.save_report(report)


if __name__ == "__main__":
    main()