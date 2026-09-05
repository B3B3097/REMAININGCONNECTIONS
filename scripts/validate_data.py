#!/usr/bin/env python3
"""Validate data files integrity."""

import json
import sys
from pathlib import Path

def validate_json(filepath):
    """Validate a JSON file."""
    print(f"Checking {filepath}...")
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            if not content.strip():
                print(f"  ❌ File is empty or whitespace only")
                return False
            data = json.loads(content)
            print(f"  ✅ Valid JSON, size: {len(content)} bytes")
            return True
    except json.JSONDecodeError as e:
        print(f"  ❌ Invalid JSON: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Error: {e}")
        return False

def main():
    data_dir = Path('data')
    files = [
        'tg_proxies_found.json',
        'utils_found.json',
        'health_metrics.json',
        'subscriptions_found.json',
        'http_proxies_found.json',
        'socks_proxies_found.json',
    ]
    
    results = []
    for filename in files:
        filepath = data_dir / filename
        if filepath.exists():
            results.append(validate_json(filepath))
        else:
            print(f"⚠️  {filepath} does not exist")
            results.append(False)
    
    print(f"\nValidation: {sum(results)}/{len(results)} files valid")
    sys.exit(0 if all(results) else 1)

if __name__ == '__main__':
    main()