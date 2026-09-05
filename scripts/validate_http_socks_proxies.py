 #!/usr/bin/env python3
"""
HTTP/SOCKS Proxy Validator for REMAININGCONNECTIONS
Validates extracted proxies by testing actual connectivity.
"""

import asyncio
import json
import sys
import logging
import argparse
from datetime import datetime, timezone
from typing import List, Dict, Optional

try:
    import aiohttp
    from aiohttp_socks import ProxyConnector, ProxyType
except ImportError:
    print("[!] Required packages not installed. Install with:")
    print("    pip install aiohttp aiohttp-socks")
    sys.exit(1)

logging.basicConfig(level=logging.INFO, format='[%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


class ProxyValidator:
    """Validate HTTP and SOCKS proxies."""
    
    TEST_URLS = [
        'http://www.gstatic.com/generate_204',
        'https://www.google.com',
    ]
    
    def __init__(self, timeout: int = 10, concurrency: int = 50):
        self.timeout = timeout
        self.concurrency = concurrency
        self.semaphore = asyncio.Semaphore(concurrency)
        
    async def test_http_proxy(self, proxy: Dict) -> Optional[Dict]:
        """Test HTTP/HTTPS proxy."""
        host = proxy.get('host')
        port = proxy.get('port')
        protocol = proxy.get('protocol', 'http')
        
        proxy_url = f"http://{host}:{port}"
        
        async with self.semaphore:
            try:
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                async with aiohttp.ClientSession(timeout=timeout) as session:
                    start_time = asyncio.get_event_loop().time()
                    
                    # Test with HTTP endpoint
                    async with session.get(
                        self.TEST_URLS[0],
                        proxy=proxy_url,
                        ssl=False
                    ) as response:
                        if response.status in [200, 204]:
                            latency = (asyncio.get_event_loop().time() - start_time) * 1000
                            
                            return {
                                'host': host,
                                'port': port,
                                'protocol': protocol,
                                'type': protocol,
                                'latency_ms': round(latency, 2),
                                'status': 'working',
                                'verified_at': datetime.now(timezone.utc).isoformat(),
                                'source': proxy.get('source', 'unknown'),
                            }
            except asyncio.TimeoutError:
                logger.debug(f"Timeout: {host}:{port}")
            except Exception as e:
                logger.debug(f"Error testing {host}:{port}: {e}")
        
        return None
    
    async def test_socks_proxy(self, proxy: Dict) -> Optional[Dict]:
        """Test SOCKS4/SOCKS5 proxy."""
        host = proxy.get('host')
        port = proxy.get('port')
        protocol = proxy.get('protocol', 'socks5')
        
        # Determine SOCKS type
        if protocol == 'socks4':
            proxy_type = ProxyType.SOCKS4
        else:
            proxy_type = ProxyType.SOCKS5
        
        async with self.semaphore:
            try:
                connector = ProxyConnector.from_url(f'{protocol}://{host}:{port}')
                timeout = aiohttp.ClientTimeout(total=self.timeout)
                
                async with aiohttp.ClientSession(
                    connector=connector,
                    timeout=timeout
                ) as session:
                    start_time = asyncio.get_event_loop().time()
                    
                    # Test with HTTP endpoint
                    async with session.get(self.TEST_URLS[0]) as response:
                        if response.status in [200, 204]:
                            latency = (asyncio.get_event_loop().time() - start_time) * 1000
                            
                            return {
                                'host': host,
                                'port': port,
                                'protocol': protocol,
                                'type': protocol,
                                'latency_ms': round(latency, 2),
                                'status': 'working',
                                'verified_at': datetime.now(timezone.utc).isoformat(),
                                'source': proxy.get('source', 'unknown'),
                            }
            except asyncio.TimeoutError:
                logger.debug(f"Timeout: {host}:{port}")
            except Exception as e:
                logger.debug(f"Error testing {host}:{port}: {e}")
        
        return None
    
    async def validate_proxy(self, proxy: Dict) -> Optional[Dict]:
        """Validate a single proxy based on its protocol."""
        protocol = proxy.get('protocol', 'http')
        
        if protocol in ['http', 'https']:
            return await self.test_http_proxy(proxy)
        elif protocol in ['socks4', 'socks5']:
            return await self.test_socks_proxy(proxy)
        else:
            logger.warning(f"Unknown protocol: {protocol}")
            return None
    
    async def validate_all(self, proxies: List[Dict]) -> List[Dict]:
        """Validate all proxies concurrently."""
        logger.info(f"Validating {len(proxies)} proxies with concurrency={self.concurrency}")
        
        tasks = [self.validate_proxy(proxy) for proxy in proxies]
        results = await asyncio.gather(*tasks)
        
        working = [r for r in results if r is not None]
        logger.info(f"Validation complete: {len(working)}/{len(proxies)} working")
        
        return working


async def main():
    parser = argparse.ArgumentParser(description='Validate HTTP/SOCKS proxies')
    parser.add_argument('--input', required=True, help='Input JSON file with extracted proxies')
    parser.add_argument('--output', required=True, help='Output JSON file for working proxies')
    parser.add_argument('--timeout', type=int, default=10, help='Timeout per proxy (seconds)')
    parser.add_argument('--max-check', type=int, default=1000, help='Max proxies to check')
    parser.add_argument('--concurrency', type=int, default=50, help='Concurrent checks')
    parser.add_argument('--protocols', nargs='+', help='Filter by protocols (http, https, socks4, socks5)')
    
    args = parser.parse_args()
    
    # Load input
    try:
        with open(args.input, 'r', encoding='utf-8') as f:
            data = json.load(f)
            proxies = data.get('proxies', [])
    except FileNotFoundError:
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in input file: {e}")
        sys.exit(1)
    
    # Filter by protocols if specified
    if args.protocols:
        proxies = [p for p in proxies if p.get('protocol') in args.protocols]
        logger.info(f"Filtered to {len(proxies)} proxies matching protocols: {args.protocols}")
    
    # Limit number of proxies
    if len(proxies) > args.max_check:
        logger.info(f"Limiting to {args.max_check} proxies")
        proxies = proxies[:args.max_check]
    
    if not proxies:
        logger.warning("No proxies to validate")
        output = {
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'total_working': 0,
            'proxies': []
        }
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        return
    
    # Validate
    validator = ProxyValidator(timeout=args.timeout, concurrency=args.concurrency)
    working_proxies = await validator.validate_all(proxies)
    
    # Sort by latency
    working_proxies.sort(key=lambda p: p.get('latency_ms', 999999))
    
    # Save results
    output = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'total_checked': len(proxies),
        'total_working': len(working_proxies),
        'success_rate': round(len(working_proxies) / len(proxies) * 100, 2) if proxies else 0,
        'proxies': working_proxies
    }
    
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    
    logger.info(f"Saved {len(working_proxies)} working proxies to {args.output}")
    
    # Print summary
    protocols = {}
    for proxy in working_proxies:
        proto = proxy.get('protocol', 'unknown')
        protocols[proto] = protocols.get(proto, 0) + 1
    
    print("\n=== VALIDATION SUMMARY ===")
    print(f"Total checked: {len(proxies)}")
    print(f"Working: {len(working_proxies)}")
    print(f"Success rate: {output['success_rate']}%")
    print("\nBy protocol:")
    for proto, count in protocols.items():
        print(f"  {proto}: {count}")


if __name__ == '__main__':
    asyncio.run(main())