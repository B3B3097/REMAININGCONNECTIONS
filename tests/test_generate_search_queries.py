"""
Unit tests for scripts/generate_search_queries.py
Verifies query generation quality, junk filtering, and output file formats.
"""

import os
import sys
import tempfile
import unittest
from argparse import Namespace
from collections import Counter

# Add repository root and scripts to path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.join(REPO_ROOT, "scripts"))

import generate_search_queries as gsq


class TestGenerateSearchQueries(unittest.TestCase):
    def test_junk_filtration_in_harvesting(self):
        """Test that junk terms, extensions, and non-proxy software are filtered out."""
        counter = Counter()
        noisy_data = [
            "Download free pdf guide and autocad tutorial",
            "Photoshop cc full crack zip rar dmg",
            "React redux typescript nodejs app framework",
            "vless subscription node with xray and reality config",
            "mtproxy telegram proxy secret",
            "nekoray clash sing-box client for windows",
        ]
        gsq.harvest_value(noisy_data, counter)

        # Ensure junk words are NOT in the harvested counter
        banned = ["pdf", "autocad", "photoshop", "zip", "rar", "dmg", "react", "typescript", "nodejs"]
        for b in banned:
            self.assertNotIn(b, counter, f"Banned word '{b}' was harvested!")

        # Ensure legitimate proxy terms ARE harvested
        legit = ["vless", "xray", "reality", "mtproxy", "nekoray", "sing-box"]
        for term in legit:
            self.assertIn(term, counter, f"Legitimate term '{term}' was missing!")

    def test_subscription_code_queries_have_uri_schemes(self):
        """Test that subscription code queries prioritize direct URI schemes."""
        queries = gsq.generate_subscription_code_queries()
        query_texts = [q["query"] for q in queries]

        # Must include fundamental URI schemes
        self.assertIn("vless://", query_texts)
        self.assertIn("vmess://", query_texts)
        self.assertIn("ss://", query_texts)
        self.assertIn("trojan://", query_texts)

        # Must not produce bare generic 'in:file'
        for q in query_texts:
            self.assertFalse(q.endswith("in:file"), f"Overly broad in:file query found: {q}")

    def test_tg_proxy_queries_are_strictly_telegram(self):
        """Test that TG proxy code queries only include Telegram markers."""
        queries = gsq.generate_tg_proxy_code_queries()
        query_texts = [q["query"] for q in queries]

        # Must include direct tg proxy links
        self.assertIn("tg://proxy", query_texts)
        self.assertIn("t.me/proxy", query_texts)
        self.assertIn("mtproxy secret", query_texts)

        # Must NOT include bare generic terms
        for q in query_texts:
            self.assertNotEqual(q, "proxy")
            self.assertNotEqual(q, "proxies")
            self.assertNotEqual(q, "secret")

    def test_utilities_code_and_topic_queries_are_targeted(self):
        """Test that utility queries target real proxy tools and circumvention topics."""
        code_queries = gsq.generate_utilities_code_queries()
        code_texts = [q["query"] for q in code_queries]

        # Must contain known tools
        has_tool = any(any(tool in q for tool in ["v2ray", "clash", "sing-box", "nekoray", "flclash"]) for q in code_texts)
        self.assertTrue(has_tool, "No known proxy tools found in utility code queries")

        # Must NOT contain bare filename queries without a tool or protocol
        for q in code_texts:
            first_term = q.split()[0]
            self.assertNotIn(first_term, ["client", "gui", "app", "application", "desktop", "mobile", "release"])

        topic_queries = gsq.generate_utilities_topic_queries()
        topic_texts = [q["query"] for q in topic_queries]
        banned_topics = ["topic:app", "topic:gui", "topic:client", "topic:release", "topic:android", "topic:windows"]
        for bt in banned_topics:
            self.assertNotIn(bt, topic_texts, f"Overly generic topic query found: {bt}")

    def test_full_generate_all_execution(self):
        """Test the end-to-end generate_all runner produces complete valid structures."""
        with tempfile.TemporaryDirectory() as tmpdir:
            args = Namespace(
                output_dir=tmpdir,
                target="Throne",
                target_aliases=["throne-app"],
                existing_data=[],
                adaptive_terms=10,
                max_repo_queries=50,
                max_code_queries=50,
                max_topic_queries=20,
                max_gitverse_queries=20,
                seed=42,
            )
            payload = gsq.generate_all(args)

            self.assertIn("categories", payload)
            self.assertIn("subscriptions", payload["categories"])
            self.assertIn("tg_proxies", payload["categories"])
            self.assertIn("utilities", payload["categories"])
            self.assertIn("target", payload["categories"])

            self.assertGreater(len(payload["categories"]["subscriptions"]["code"]), 0)
            self.assertGreater(len(payload["categories"]["tg_proxies"]["code"]), 0)
            self.assertGreater(len(payload["categories"]["utilities"]["repo"]), 0)
            self.assertGreater(len(payload["categories"]["target"]["mixed"]), 0)


if __name__ == "__main__":
    unittest.main()
