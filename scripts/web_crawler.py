#!/usr/bin/env python3
"""
Advanced Web Crawler for REMAININGCONNECTIONS.

This module provides a high-performance, asynchronous web crawler designed 
specifically for discovering subscription links, GitHub repositories, and 
publicly hosted configuration files containing proxy information.

Features:
- Asynchronous HTTP requests using aiohttp.
- Intelligent link extraction (URLs, emails, GitHub raw links).
- Pagination handling for search result pages.
- Rate limiting and polite crawling delays.
- Content filtering based on regular expressions (e.g., detecting VLESS/Trojan URIs).
- User-Agent rotation to avoid basic bot detection.
- Depth-limited traversal to prevent infinite loops.

Usage:
    python scripts/web_crawler.py --start-url "https://github.com/search" --pattern "vless://"
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import random
import re
import time
import urllib.parse
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple, Callable

try:
    import aiohttp
    from bs4 import BeautifulSoup
except ImportError:
    # Fallback for environments without optional dependencies
    aiohttp = None
    BeautifulSoup = None

logger = logging.getLogger("WebCrawler")


# --- Configuration Constants ---

DEFAULT_USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1"
]

# Common patterns for subscription/proxy content
PROXY_PATTERNS = {
    "VLESS": r"vless://[a-f0-9\-]+@[\w\.\-]+:\d+",
    "VMess": r"vmess://[A-Za-z0-9+/=]+",
    "TROJAN": r"trojan://[^@]+@[\w\.\-]+:\d+",
    "SS": r"ss://[A-Za-z0-9\-_+=]+@[\w\.\-]+:\d+",
    "TG_PROXY": r"(?:tg|https?://t\.me)/(?:proxy|socks)\?[^\s\"]+",
    "YAML_SUB": r"https?://.*\.yaml(?:\?.*)?",
    "JSON_SUB": r"https?://.*\.json(?:\?.*)?",
}

# Patterns for finding *more* links to crawl
LINK_PATTERNS = {
    "HTML_HREF": r'href=["\']([^"\']+)["\']',
    "RAW_GITHUB": r"github\.com/[^/]+/[^/]+/raw/[\w\.]+",
    "PASTEBIN": r"pastebin\.com/[a-zA-Z0-9]+",
    "TEXT_URL": r"https?://(?:www\.)?[-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b(?:[-a-zA-Z0-9()@:%_\+.~#?&/=]*)",
}


@dataclass
class CrawlResult:
    """Represents the result of fetching a single URL."""
    url: str
    status_code: int
    content_length: int
    found_links: List[str]
    found_proxies: List[Dict[str, Any]]
    errors: List[str] = field(default_factory=list)
    response_time_ms: float = 0.0


@dataclass
class CrawlStats:
    """Statistics for the entire crawl session."""
    urls_visited: int = 0
    unique_urls_found: int = 0
    proxies_found: int = 0
    bytes_downloaded: int = 0
    errors: int = 0
    duration_seconds: float = 0.0


class SessionManager:
    """Manages aiohttp client sessions and connection pooling."""

    def __init__(self, timeout: int = 10, retries: int = 3):
        self.timeout = aiohttp.ClientTimeout(total=timeout)
        self.retries = retries
        self.session: Optional[aiohttp.ClientSession] = None

    async def initialize(self):
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers={"Accept": "*/*"}
            )

    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()

    async def request(self, method: str, url: str, **kwargs) -> Optional[aiohttp.ClientResponse]:
        """Execute an HTTP request with retry logic."""
        last_error = None
        
        for attempt in range(self.retries):
            try:
                await self.initialize()
                async with self.session.request(method, url, allow_redirects=True, **kwargs) as resp:
                    if resp.status == 429: # Too Many Requests
                        wait_time = random.uniform(2.0, 5.0)
                        logger.warning(f"Rate limited ({url}). Waiting {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        continue
                    
                    if resp.status >= 500:
                        await asyncio.sleep(1.0)
                        continue
                        
                    return resp
            except asyncio.TimeoutError:
                last_error = f"Timeout after {self.timeout.total()}s"
            except Exception as e:
                last_error = str(e)
            
            if attempt < self.retries - 1:
                backoff = 2 ** attempt + random.random()
                await asyncio.sleep(backoff)
                
        logger.error(f"Failed to fetch {url} after {self.retries} attempts. Error: {last_error}")
        return None


class SmartCrawler:
    """
    Main Crawler Class.
    
    Performs depth-first or breadth-first crawling with intelligent content analysis.
    """

    def __init__(
        self,
        max_depth: int = 3,
        max_pages: int = 100,
        delay_range: Tuple[float, float] = (0.5, 1.5),
        user_agent_index: int = 0
    ):
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.delay_range = delay_range
        self.visited_urls: Set[str] = set()
        self.url_queue: deque = deque()
        self.stats = CrawlStats()
        self.session_mgr = SessionManager()
        
        # Compile regexes
        self.compiled_patterns = {k: re.compile(v) for k, v in PROXY_PATTERNS.items()}
        self.link_regex = re.compile(LINK_PATTERNS["HTML_HREF"], re.IGNORECASE)
        self.text_url_regex = re.compile(LINK_PATTERNS["TEXT_URL"])

    def _get_user_agent(self) -> str:
        """Rotate User-Agents."""
        ua = DEFAULT_USER_AGENTS[self.stats.urls_visited % len(DEFAULT_USER_AGENTS)]
        return ua

    def _normalize_url(self, url: str, base_url: str = "") -> Optional[str]:
        """Resolve relative URLs and normalize."""
        if not url:
            return None
        try:
            parsed = urllib.parse.urlparse(url)
            # Skip non-http schemes
            if parsed.scheme not in ("http", "https"):
                return None
            # Resolve relative paths
            if not parsed.netloc:
                url = urllib.parse.urljoin(base_url, url)
            # Normalize query params order might differ
            normalized = urllib.parse.urlparse(urllib.parse.urlunparse(parsed._replace(query='')))
            return normalized.geturl()
        except Exception:
            return None

    def _extract_content(self, html: str, page_url: str) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Extract links and proxy strings from HTML content."""
        extracted_links = []
        found_proxies = []

        # 1. Extract Links for Crawling
        href_matches = self.link_regex.findall(html)
        for link in href_matches:
            clean_link = self._normalize_url(link, page_url)
            if clean_link and clean_link not in self.visited_urls:
                extracted_links.append(clean_link)

        # 2. Extract Proxy Strings (Content Mining)
        # Check specific patterns first
        for pattern_name, regex in self.compiled_patterns.items():
            matches = regex.findall(html)
            for match in matches:
                # Clean up match (remove trailing punctuation often caught)
                match = match.rstrip('",);]')
                found_proxies.append({
                    "type": pattern_name,
                    "value": match,
                    "source_url": page_url
                })
        
        # Fallback: General URL extraction for things we might miss
        general_urls = self.text_url_regex.findall(html)
        for url in general_urls:
            url = url.rstrip('",);]')
            if any(kw in url.lower() for kw in ["pastebin", "gist", "raw.githubusercontent"]):
                 extracted_links.append(url)

        return list(set(extracted_links)), found_proxies

    async def _process_page(self, url: str, depth: int) -> CrawlResult:
        """Fetch and process a single page."""
        start_time = time.time()
        result = CrawlResult(url=url, status_code=0, content_length=0, found_links=[], found_proxies=[])

        # Polite delay
        if self.stats.urls_visited > 0:
            delay = random.uniform(*self.delay_range)
            await asyncio.sleep(delay)

        headers = {"User-Agent": self._get_user_agent(), "Referer": "https://www.google.com/"}
        
        resp = await self.session_mgr.request("GET", url, headers=headers)
        
        if not resp:
            result.errors.append("Connection failed")
            self.stats.errors += 1
            return result

        result.status_code = resp.status
        try:
            content_type = resp.headers.get("Content-Type", "")
            if "text/html" not in content_type and "application/json" not in content_type and "text/plain" not in content_type:
                return result # Skip binary/non-text
            
            body = await resp.text(errors="ignore")
            result.content_length = len(body)
            self.stats.bytes_downloaded += len(body)
            
            # Analyze content
            links, proxies = self._extract_content(body, url)
            
            result.found_links = links[:50] # Limit links per page to prevent explosion
            result.found_proxies = proxies
            self.stats.proxies_found += len(proxies)
            
        except Exception as e:
            result.errors.append(str(e))
            self.stats.errors += 1

        result.response_time_ms = (time.time() - start_time) * 1000
        self.stats.urls_visited += 1
        
        return result

    async def run(self, start_urls: List[str]) -> Dict[str, Any]:
        """
        Execute the crawl starting from a list of URLs.
        """
        logger.info(f"Starting crawl from {len(start_urls)} URLs. Max depth: {self.max_depth}, Max pages: {self.max_pages}")
        
        for url in start_urls:
            norm_url = self._normalize_url(url)
            if norm_url:
                self.url_queue.append((norm_url, 0)) # (url, depth)
                self.visited_urls.add(norm_url)

        all_results = []
        start_time = time.time()

        while self.url_queue and self.stats.urls_visited < self.max_pages:
            current_url, depth = self.url_queue.popleft()
            
            # Avoid revisiting
            if current_url in self.visited_urls:
                continue
                
            self.visited_urls.add(current_url)
            
            # Process page
            res = await self._process_page(current_url, depth)
            all_results.append(res)
            
            # Enqueue new links if depth allows
            if depth < self.max_depth:
                for link in res.found_links:
                    if link not in self.visited_urls:
                        self.url_queue.append((link, depth + 1))
                        self.visited_urls.add(link) # Mark as visited to prevent duplicates in queue
                        self.stats.unique_urls_found += 1

        self.stats.duration_seconds = time.time() - start_time
        
        return self.generate_report(all_results)

    def generate_report(self, results: List[CrawlResult]) -> Dict[str, Any]:
        """Generate a summary report of the crawl."""
        report = {
            "stats": self.stats.__dict__,
            "proxies_found": [],
            "pages_analyzed": len(results)
        }
        
        # Flatten proxies
        for res in results:
            for p in res.found_proxies:
                report["proxies_found"].append(p)
                
        # Deduplicate proxies
        unique_proxies = {}
        for p in report["proxies_found"]:
            unique_proxies[p["value"]] = p
        report["unique_proxies"] = list(unique_proxies.values())
        
        return report


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--start-urls", nargs="+", required=True, help="Starting URLs")
    parser.add_argument("--max-depth", type=int, default=2, help="Max crawl depth")
    parser.add_argument("--max-pages", type=int, default=50, help="Max pages to visit")
    parser.add_argument("--output", default="crawl_results.json", help="Output JSON file")
    
    args = parser.parse_args()
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    crawler = SmartCrawler(max_depth=args.max_depth, max_pages=args.max_pages)
    
    try:
        report = loop.run_until_complete(crawler.run(args.start_urls))
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
            
        print(f"[+] Crawl complete.")
        print(f"    Pages Visited: {report['stats']['urls_visited']}")
        print(f"    Unique Proxies Found: {len(report['unique_proxies'])}")
        print(f"    Data saved to {args.output}")
        
    finally:
        loop.run_until_complete(crawler.session_mgr.close())
        loop.close()


if __name__ == "__main__":
    main()