 #!/usr/bin/env python3
"""
HTTP/SOCKS Proxy Extractor for REMAININGCONNECTIONS
Searches GitHub for proxy lists and extracts HTTP, HTTPS, SOCKS4, SOCKS5 proxies.
"""

import asyncio
import json
import os
import re
import sys
import logging
from datetime import datetime, timezone
from typing import List, Dict, Set

try:
    import aiohttp
except ImportError:
    print("[!] aiohttp not installed. Install with: pip install aiohttp")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class ProxyExtractor:
    """Extract HTTP/SOCKS proxies from GitHub repositories."""
    
    # Proxy patterns
    PROXY_PATTERNS = {
        'ip_port': r'\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}\b',
        'http_url': r'https?://(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}',
        'socks_url': r'socks[45]://(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}',
    }
    
    SEARCH_QUERIES = [
        'proxy list',
        'free proxy',
        'http proxy list',
        'socks proxy list',
        'socks5 proxy',
        'proxy.txt',
        'proxies.json',
        'working proxies',
    ]
    
    def __init__(self, github_token: str = None, max_results: int = 1000):
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.max_results = max_results
        self.session = None
        self.found_proxies = set()
        
    async def __aenter__(self):
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'REMAININGCONNECTIONS-PROXY-EXTRACTOR/1.0'
        }
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        self.session = aiohttp.ClientSession(headers=headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def detect_protocol(self, text: str, context: str = '') -> str:
        """Detect proxy protocol from URL or context."""
        text_lower = text.lower()
        context_lower = context.lower()
        
        if 'socks5://' in text_lower or 'socks5' in context_lower:
            return 'socks5'
        elif 'socks4://' in text_lower or 'socks4' in context_lower:
            return 'socks4'
        elif 'https://' in text_lower or 'https' in context_lower:
            return 'https'
        elif 'http://' in text_lower or 'http' in context_lower:
            return 'http'
        
        # Default based on file context
        if 'socks' in context_lower:
            return 'socks5'
        return 'http'
    
    def parse_proxy(self, text: str, context: str = '') -> Dict:
        """Parse proxy string into structured format."""
        try:
            # Remove protocol prefix if present
            clean_text = re.sub(r'^(https?|socks[45])://', '', text)
            
            # Extract host:port
            match = re.match(r'^([\d\.]+):(\d+)$', clean_text)
            if not match:
                return None
            
            host = match.group(1)
            port = int(match.group(2))
            
            # Validate IP
            octets = host.split('.')
            if len(octets) != 4 or not all(0 <= int(o) <= 255 for o in octets):
                return None
            
            # Validate port
            if not (1 <= port <= 65535):
                return None
            
            protocol = self.detect_protocol(text, context)
            
            return {
                'host': host,
                'port': port,
                'protocol': protocol,
                'type': protocol,
            }
        except Exception as e:
            logger.debug(f"Failed to parse proxy {text}: {e}")
            return None
    
    def extract_proxies_from_content(self, content: str, filename: str = '') -> List[Dict]:
        """Extract all proxies from text content."""
        proxies = []
        
        # Try each pattern
        for pattern_name, pattern in self.PROXY_PATTERNS.items():
            matches = re.finditer(pattern, content, re.MULTILINE)
            for match in matches:
                text = match.group(0)
                proxy = self.parse_proxy(text, filename)
                
                if proxy:
                    proxy_key = f"{proxy['host']}:{proxy['port']}"
                    if proxy_key not in self.found_proxies:
                        self.found_proxies.add(proxy_key)
                        proxies.append(proxy)
        
        return proxies
    
    async def search_github_code(self, query: str, max_pages: int = 3) -> List[Dict]:
        """Search GitHub code for the given query."""
        all_proxies = []
        
        for page in range(1, max_pages + 1):
            try:
                url = f'https://api.github.com/search/code?q={query}&per_page=100&page={page}'
                async with self.session.get(url) as resp:
                    if resp.status == 403:
                        logger.warning(f"Rate limited on query '{query}', page {page}")
                        await asyncio.sleep(60)
                        continue
                    elif resp.status != 200:
                        logger.warning(f"GitHub returned {resp.status} for '{query}'")
                        break
                    
                    data = await resp.json()
                    items = data.get('items', [])
                    
                    if not items:
                        break
                    
                    logger.info(f"Query '{query}' page {page}: {len(items)} results")
                    
                    # Fetch file contents
                    for item in items[:15]:  # Limit to 15 files per page
                        try:
                            content_url = item.get('url')
                            filename = item.get('name', '')
                            
                            async with self.session.get(content_url) as content_resp:
                                if content_resp.status == 200:
                                    content_data = await content_resp.json()
                                    content = content_data.get('content', '')
                                    
                                    # Decode base64
                                    import base64
                                    try:
                                        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                                        proxies = self.extract_proxies_from_content(decoded, filename)
                                        
                                        # Add source info
                                        for proxy in proxies:
                                            proxy['source'] = item.get('repository', {}).get('full_name', 'unknown')
                                            proxy['found_at'] = datetime.now(timezone.utc).isoformat()
                                        
                                        all_proxies.extend(proxies)
                                        if proxies:
                                            logger.info(f"Extracted {len(proxies)} proxies from {filename}")
                                    except Exception as e:
                                        logger.debug(f"Failed to decode content: {e}")
                                        
                            await asyncio.sleep(0.5)  # Rate limiting
                        except Exception as e:
                            logger.debug(f"Error fetching file content: {e}")
                    
                    await asyncio.sleep(2)  # Rate limiting between pages
                    
            except Exception as e:
                logger.error(f"Error searching GitHub for '{query}': {e}")
                break
        
        return all_proxies
    
    async def extract_all(self) -> Dict[str, List[Dict]]:
        """Extract proxies from all search queries."""
        all_proxies = []
        
        logger.info(f"Starting proxy extraction with {len(self.SEARCH_QUERIES)} queries")
        
        for query in self.SEARCH_QUERIES:
            proxies = await self.search_github_code(query, max_pages=2)
            all_proxies.extend(proxies)
            
            if len(all_proxies) >= self.max_results:
                logger.info(f"Reached max results limit ({self.max_results})")
                break
            
            await asyncio.sleep(5)  # Rate limiting between queries
        
        # Deduplicate
        unique_proxies = {}
        for proxy in all_proxies:
            key = f"{proxy['host']}:{proxy['port']}"
            if key not in unique_proxies:
                unique_proxies[key] = proxy
        
        # Split by protocol
        http_proxies = []
        socks_proxies = []
        
        for proxy in unique_proxies.values():
            protocol = proxy.get('protocol', 'http')
            if protocol in ['http', 'https']:
                http_proxies.append(proxy)
            elif protocol in ['socks4', 'socks5']:
                socks_proxies.append(proxy)
        
        logger.info(f"Extracted {len(http_proxies)} HTTP/HTTPS proxies")
        logger.info(f"Extracted {len(socks_proxies)} SOCKS proxies")
        
        return {
            'http': http_proxies,
            'socks': socks_proxies
        }


async def main():
    """Main extraction function."""
    os.makedirs('extracted', exist_ok=True)
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        logger.warning("GITHUB_TOKEN not set. Rate limits will be very restrictive.")
    
    async with ProxyExtractor(github_token=github_token, max_results=1000) as extractor:
        proxies_by_type = await extractor.extract_all()
    
    # Save HTTP proxies
    http_output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_extracted': len(proxies_by_type['http']),
        'proxies': proxies_by_type['http']
    }
    
    with open('extracted/http_proxies_extracted.json', 'w', encoding='utf-8') as f:
        json.dump(http_output, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(proxies_by_type['http'])} HTTP proxies to extracted/http_proxies_extracted.json")
    
    # Save SOCKS proxies
    socks_output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_extracted': len(proxies_by_type['socks']),
        'proxies': proxies_by_type['socks']
    }
    
    with open('extracted/socks_proxies_extracted.json', 'w', encoding='utf-8') as f:
        json.dump(socks_output, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(proxies_by_type['socks'])} SOCKS proxies to extracted/socks_proxies_extracted.json")
    
    # Print summary
    print("\n=== EXTRACTION SUMMARY ===")
    print(f"HTTP/HTTPS proxies: {len(proxies_by_type['http'])}")
    print(f"SOCKS proxies: {len(proxies_by_type['socks'])}")
    print(f"Total unique: {len(proxies_by_type['http']) + len(proxies_by_type['socks'])}")


if __name__ == '__main__':
    asyncio.run(main())