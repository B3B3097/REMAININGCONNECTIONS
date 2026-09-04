#!/usr/bin/env python3
"""
Batch Proxy Validator for REMAININGCONNECTIONS
Performs deep validation (TCP, TLS handshake, latency) on a list of proxies.
"""

import asyncio
import argparse
import json
import logging
import os
import socket
import ssl
import time
from urllib.parse import urlparse

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

TIMEOUT = 8
MAX_RETRIES = 2


def parse_proxy_uri(uri):
    """Parse a proxy URI string into components."""
    try:
        parsed = urlparse(uri)
        scheme = parsed.scheme.lower() if parsed.scheme else ''
        hostname = parsed.hostname or ''
        port = parsed.port
        return {
            'protocol': scheme,
            'server': hostname,
            'port': port,
            'uri': uri,
        }
    except Exception as e:
        logger.debug(f"Failed to parse URI '{uri}': {e}")
        return None


async def check_tcp_connection(host, port, timeout=TIMEOUT):
    """Attempt TCP connection and measure latency."""
    start = time.monotonic()
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout
        )
        latency_ms = (time.monotonic() - start) * 1000
        writer.close()
        await writer.wait_closed()
        return True, latency_ms
    except (asyncio.TimeoutError, ConnectionRefusedError, OSError) as e:
        latency_ms = (time.monotonic() - start) * 1000
        logger.debug(f"TCP check failed for {host}:{port} - {e}")
        return False, latency_ms


async def check_tls_handshake(host, port, timeout=TIMEOUT):
    """Attempt TLS handshake and extract cipher info."""
    start = time.monotonic()
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE

        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port, ssl=ctx),
            timeout=timeout
        )
        latency_ms = (time.monotonic() - start) * 1000

        # Get cipher info
        ssl_obj = writer.get_extra_info('ssl_object')
        cipher = None
        if ssl_obj:
            cipher_info = ssl_obj.cipher()
            if cipher_info:
                cipher = cipher_info[0]

        writer.close()
        await writer.wait_closed()
        return True, latency_ms, cipher
    except (asyncio.TimeoutError, ssl.SSLError, ConnectionRefusedError, OSError) as e:
        latency_ms = (time.monotonic() - start) * 1000
        logger.debug(f"TLS check failed for {host}:{port} - {e}")
        return False, latency_ms, None


def calculate_deep_score(tcp_ok, tcp_latency, tls_ok, tls_latency, cipher):
    """Calculate a composite score (0-100) for a proxy."""
    score = 0.0

    if tcp_ok:
        score += 40.0
        # Lower latency = higher score (max 20 points for <100ms)
        if tcp_latency < 100:
            score += 20.0
        elif tcp_latency < 300:
            score += 15.0
        elif tcp_latency < 1000:
            score += 10.0
        else:
            score += 5.0

    if tls_ok:
        score += 30.0
        if cipher:
            score += 10.0

    return round(score, 1)


async def validate_proxy(proxy, index, semaphore):
    """Validate a single proxy with concurrency control."""
    async with semaphore:
        server = proxy.get('server', '')
        port = proxy.get('port', 0)
        protocol = proxy.get('protocol', '')

        if not server or not port:
            return {**proxy, 'working': False, 'deep_score': 0.0, 'error': 'missing server/port'}

        logger.info(f"[{index}] Validating {protocol}://{server}:{port}")

        # TCP check
        tcp_ok, tcp_latency = await check_tcp_connection(server, port)

        # TLS check (only if TCP succeeded)
        tls_ok = False
        tls_latency = 0.0
        cipher = None
        if tcp_ok:
            tls_ok, tls_latency, cipher = await check_tls_handshake(server, port)

        score = calculate_deep_score(tcp_ok, tcp_latency, tls_ok, tls_latency, cipher)

        result = {
            **proxy,
            'working': tcp_ok,
            'tcp_latency_ms': round(tcp_latency, 2),
            'tls_latency_ms': round(tls_latency, 2),
            'tls_cipher': cipher,
            'handshake_success': tls_ok,
            'deep_score': score,
        }

        status = "OK" if tcp_ok else "FAIL"
        logger.info(f"[{index}] {status} {server}:{port} score={score} tcp={tcp_latency:.0f}ms")
        return result


async def run_validation(proxies, concurrency):
    """Run validation on all proxies with bounded concurrency."""
    semaphore = asyncio.Semaphore(concurrency)
    tasks = [
        validate_proxy(proxy, idx + 1, semaphore)
        for idx, proxy in enumerate(proxies)
    ]
    return await asyncio.gather(*tasks)


def main():
    parser = argparse.ArgumentParser(description='Batch Proxy Deep Validator')
    parser.add_argument('--input', required=True, help='Input JSON file with proxies')
    parser.add_argument('--output', required=True, help='Output JSON file for results')
    parser.add_argument('--concurrency', type=int, default=20, help='Max concurrent checks')
    args = parser.parse_args()

    # Load input
    if not os.path.exists(args.input):
        logger.error(f"Input file not found: {args.input}")
        sys.exit(1)

    with open(args.input, 'r', encoding='utf-8') as f:
        data = json.load(f)

    proxies = data.get('proxies', [])
    if not proxies:
        logger.warning("No proxies found in input file.")
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump({"proxies": [], "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}, f, indent=2)
        return

    logger.info(f"Loaded {len(proxies)} proxies for validation. Concurrency: {args.concurrency}")

    # Filter valid proxies
    valid_proxies = []
    for idx, proxy in enumerate(proxies):
        protocol_str = proxy.get('protocol', '')
        if not protocol_str:
            uri = proxy.get('uri', '')
            parsed = parse_proxy_uri(uri)
            if parsed:
                proxy['protocol'] = parsed['protocol']
                proxy['server'] = proxy.get('server') or parsed['server']
                proxy['port'] = proxy.get('port') or parsed['port']
                valid_proxies.append(proxy)
            else:
                logger.warning(f"Skipping proxy {idx}: unparseable URI")
                continue
        elif protocol_str.lower() in ('vless', 'vmess', 'ss', 'trojan', 'hysteria2', 'hy2', 'tuic', 'mtproto', 'http', 'https', 'socks5'):
            valid_proxies.append(proxy)
        else:
            logger.warning(f"Skipping unsupported or invalid protocol for proxy {idx}: {protocol_str}")
            continue

    logger.info(f"Valid proxies to check: {len(valid_proxies)}")

    # Run async validation
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        results = loop.run_until_complete(run_validation(valid_proxies, args.concurrency))
    finally:
        loop.close()

    # Summarize
    working = [r for r in results if r.get('working')]
    logger.info(f"Validation complete: {len(working)}/{len(results)} proxies working")

    # Write output
    output = {
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_checked": len(results),
        "total_working": len(working),
        "proxies": results,
    }

    os.makedirs(os.path.dirname(args.output) if os.path.dirname(args.output) else '.', exist_ok=True)
    with open(args.output, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    logger.info(f"Results saved to {args.output}")


if __name__ == '__main__':
    main()