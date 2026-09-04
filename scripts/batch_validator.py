#!/usr/bin/env python3
"""Batch Validator Runner for REMAININGCONNECTIONS.

This script acts as a bridge between the raw proxy data JSON and the 
Advanced Validator Engine. It loads proxies, prepares configurations, 
runs the validation suite, and updates the JSON file with new metrics.

Usage:
    python scripts/batch_validator.py --input data/tg_proxies_found.json --output data/deep_checked.json
"""

import asyncio
import json
import sys
import logging
from pathlib import Path
from typing import Any, Dict, List

# Ensure scripts directory is in path
sys.path.insert(0, str(Path(__file__).parent))

from advanced_validator import (
    DeepValidator, ValidationConfig, Protocol, ClientFingerprint, ValidationResult
)

logger = logging.getLogger("BatchValidator")


class BatchProcessor:
    """Orchestrates the batch validation process."""

    def __init__(self, concurrency: int = 10, timeout: float = 8.0):
        self.validator = DeepValidator(concurrency=concurrency, timeout=timeout)
        self.batch_size = 50  # Process in chunks to manage memory

    async def process_file(self, input_path: str, output_path: str) -> Dict[str, Any]:
        """Load proxies, validate, and save results."""
        logger.info(f"Loading proxies from {input_path}...")
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load input file: {e}")
            return {}

        proxies = data.get("proxies", [])
        total = len(proxies)
        logger.info(f"Found {total} proxies. Starting validation...")

        # Prepare configs
        configs = []
        for idx, proxy in enumerate(proxies):
            protocol_str = proxy.get("protocol", "").upper()
            
            # Map protocol string to Enum
            protocol_enum = None
            if protocol_str == "VLESS":
                protocol_enum = Protocol.VLESS
            elif protocol_str == "VMESS":
                protocol_enum = Protocol.VMESS
            elif protocol_str == "TROJAN":
                protocol_enum = Protocol.TROJAN
            elif protocol_str == "SS" or protocol_str == "SHADOWSOCKS":
                protocol_enum = Protocol.SHADOWSOCKS
            elif protocol_str == "HYSTERIA2" or protocol_str == "HY2":
                protocol_enum = Protocol.HYPERSIA_2
            elif protocol_str == "MTPROTO":
                # MTProto validation is different, skipping for now or adding specific handler
                continue
            else:
                continue

            if not protocol_enum:
                continue

            config = ValidationConfig(
                target_host=proxy.get("server"),
                target_port=proxy.get("port"),
                protocol=protocol_enum,
                secret_or_uuid=proxy.get("secret"),
                sni=proxy.get("sni"),
                fingerprint=ClientFingerprint.CHROME_120,
                enable_tls_check=True,
                enable_handshake_check=True
            )
            configs.append((idx, config))

        logger.info(f"Prepared {len(configs)} valid configs for validation.")

        # Validate in chunks
        validated_results = {}
        for i in range(0, len(configs), self.batch_size):
            chunk = configs[i:i + self.batch_size]
            logger.info(f"Processing chunk {i//self.batch_size + 1}...")
            
            chunk_configs = [c[1] for c in chunk]
            indices = [c[0] for c in chunk]
            
            results = await self.validator.batch_validate(chunk_configs)
            
            for res, orig_idx in zip(results, indices):
                validated_results[orig_idx] = res

        # Update original data
        logger.info("Updating proxy data with validation results...")
        updated_proxies = []
        stats = {"success": 0, "fail": 0, "skipped": 0}

        for idx, proxy in enumerate(proxies):
            if idx in validated_results:
                res = validated_results[idx]
                
                # Update proxy fields
                proxy["deep_score"] = res.score
                proxy["tcp_latency_ms"] = res.tcp_latency_ms
                proxy["tls_cipher"] = res.tls_cipher
                proxy["handshake_success"] = res.handshake_success
                
                # Determine final status
                if res.score > 70 and res.handshake_success:
                    proxy["status"] = "working"
                    stats["success"] += 1
                elif res.score < 30:
                    proxy["status"] = "failed"
                    stats["fail"] += 1
                else:
                    proxy["status"] = "unverified"
                    stats["fail"] += 1 # Treat inconclusive as failed for safety
                    
                updated_proxies.append(proxy)
            else:
                stats["skipped"] += 1
                updated_proxies.append(proxy)

        data["proxies"] = updated_proxies
        data["validation_stats"] = stats
        data["generated_at"] = __import__('datetime').datetime.utcnow().isoformat()

        # Save output
        output_p = Path(output_path)
        output_p.parent.mkdir(parents=True, exist_ok=True)
        with open(output_p, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        logger.info(f"Saved results to {output_path}")
        logger.info(f"Stats: Success={stats['success']}, Fail={stats['fail']}, Skipped={stats['skipped']}")
        
        return data

    def run(self, input_file: str, output_file: str):
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self.process_file(input_file, output_file))
        finally:
            loop.close()


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", default="data/tg_proxies_found.json", help="Input JSON file")
    parser.add_argument("--output", default="data/deep_checked.json", help="Output JSON file")
    parser.add_argument("--concurrency", type=int, default=10, help="Parallel workers")
    
    args = parser.parse_args()
    
    processor = BatchProcessor(concurrency=args.concurrency)
    processor.run(args.input, args.output)


if __name__ == "__main__":
    main()