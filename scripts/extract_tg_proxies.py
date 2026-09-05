 #!/usr/bin/env python3
"""
Telegram Proxy Extractor for REMAININGCONNECTIONS
Searches GitHub for Telegram proxy configurations and extracts them.
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


class TelegramProxyExtractor:
    """Extract Telegram proxies from GitHub repositories."""
    
    # Telegram proxy URL patterns
    TG_PROXY_PATTERNS = [
        # tg://proxy?server=...&port=...&secret=...
        r'tg://proxy\?[^\s<>"\']+',
        # https://t.me/proxy?server=...&port=...&secret=...
        r'https?://t\.me/proxy\?[^\s<>"\']+',
        # Direct mtproto format: server:port:secret
        r'\b(?:\d{1,3}\.){3}\d{1,3}:\d{2,5}:[a-fA-F0-9]{32,}\b',
        # Domain:port:secret
        r'\b[a-z0-9.-]+\.[a-z]{2,}:\d{2,5}:[a-fA-F0-9]{32,}\b',
    ]
    
    SEARCH_QUERIES = [
        'tg://proxy',
        't.me/proxy',
        'mtproto proxy',
        'mtproxy secret',
        'telegram proxy secret',
        'dd secret telegram',
        'ee secret mtproto',
    ]
    
    def __init__(self, github_token: str = None, max_results: int = 500):
        self.github_token = github_token or os.getenv('GITHUB_TOKEN')
        self.max_results = max_results
        self.session = None
        self.found_proxies = set()
        
    async def __aenter__(self):
        headers = {
            'Accept': 'application/vnd.github.v3+json',
            'User-Agent': 'REMAININGCONNECTIONS-TG-EXTRACTOR/1.0'
        }
        if self.github_token:
            headers['Authorization'] = f'token {self.github_token}'
        
        self.session = aiohttp.ClientSession(headers=headers)
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    def parse_tg_url(self, url: str) -> Dict:
        """Parse Telegram proxy URL into structured format."""
        try:
            # Extract parameters from URL
            server_match = re.search(r'server=([^&\s]+)', url)
            port_match = re.search(r'port=(\d+)', url)
            secret_match = re.search(r'secret=([a-fA-F0-9]+)', url)
            
            if not (server_match and port_match and secret_match):
                return None
                
            return {
                'host': server_match.group(1),
                'port': int(port_match.group(1)),
                'secret': secret_match.group(1),
                'protocol': 'mtproto',
                'type': 'mtproto'
            }
        except Exception as e:
            logger.debug(f"Failed to parse URL {url}: {e}")
            return None
    
    def parse_direct_format(self, text: str) -> Dict:
        """Parse direct format: host:port:secret"""
        try:
            parts = text.split(':')
            if len(parts) < 3:
                return None
                
            host = parts[0]
            port = int(parts[1])
            secret = parts[2]
            
            # Validate
            if not (1 <= port <= 65535):
                return None
            if len(secret) < 32 or not re.match(r'^[a-fA-F0-9]+$', secret):
                return None
                
            return {
                'host': host,
                'port': port,
                'secret': secret,
                'protocol': 'mtproto',
                'type': 'mtproto'
            }
        except Exception as e:
            logger.debug(f"Failed to parse direct format {text}: {e}")
            return None
    
    def extract_proxies_from_content(self, content: str) -> List[Dict]:
        """Extract all proxies from text content."""
        proxies = []
        
        for pattern in self.TG_PROXY_PATTERNS:
            matches = re.finditer(pattern, content, re.IGNORECASE)
            for match in matches:
                text = match.group(0)
                
                # Try parsing as URL
                if 'tg://' in text or 't.me' in text:
                    proxy = self.parse_tg_url(text)
                    if proxy:
                        proxy_key = f"{proxy['host']}:{proxy['port']}"
                        if proxy_key not in self.found_proxies:
                            self.found_proxies.add(proxy_key)
                            proxies.append(proxy)
                # Try parsing as direct format
                else:
                    proxy = self.parse_direct_format(text)
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
                    for item in items[:20]:  # Limit to 20 files per page
                        try:
                            content_url = item.get('url')
                            async with self.session.get(content_url) as content_resp:
                                if content_resp.status == 200:
                                    content_data = await content_resp.json()
                                    content = content_data.get('content', '')
                                    
                                    # Decode base64
                                    import base64
                                    try:
                                        decoded = base64.b64decode(content).decode('utf-8', errors='ignore')
                                        proxies = self.extract_proxies_from_content(decoded)
                                        
                                        # Add source info
                                        for proxy in proxies:
                                            proxy['source'] = item.get('repository', {}).get('full_name', 'unknown')
                                            proxy['found_at'] = datetime.now(timezone.utc).isoformat()
                                        
                                        all_proxies.extend(proxies)
                                        logger.info(f"Extracted {len(proxies)} proxies from {item.get('name')}")
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
    
    async def extract_all(self) -> List[Dict]:
        """Extract proxies from all search queries."""
        all_proxies = []
        
        logger.info(f"Starting Telegram proxy extraction with {len(self.SEARCH_QUERIES)} queries")
        
        for query in self.SEARCH_QUERIES:
            proxies = await self.search_github_code(query, max_pages=3)
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
        
        result = list(unique_proxies.values())
        logger.info(f"Extracted {len(result)} unique proxies")
        return result


async def main():
    """Main extraction function."""
    output_file = 'extracted/tg_proxies_extracted.json'
    os.makedirs('extracted', exist_ok=True)
    
    github_token = os.getenv('GITHUB_TOKEN')
    if not github_token:
        logger.warning("GITHUB_TOKEN not set. Rate limits will be very restrictive.")
    
    async with TelegramProxyExtractor(github_token=github_token, max_results=500) as extractor:
        proxies = await extractor.extract_all()
    
    # Save results
    output_data = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_extracted': len(proxies),
        'proxies': proxies
    }
    
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(output_data, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(proxies)} proxies to {output_file}")
    
    # Print summary
    protocols = {}
    for proxy in proxies:
        proto = proxy.get('protocol', 'unknown')
        protocols[proto] = protocols.get(proto, 0) + 1
    
    print("\n=== EXTRACTION SUMMARY ===")
    print(f"Total extracted: {len(proxies)}")
    print(f"Output: {output_file}")
    print("\nBy protocol:")
    for proto, count in protocols.items():
        print(f"  {proto}: {count}")


if __name__ == '__main__':
    asyncio.run(main())