 #!/usr/bin/env python3
"""
Generate summary report for all discovered proxies.
"""

import json
import os
from datetime import datetime, timezone
from typing import Dict, List

def load_json_safe(filepath: str) -> Dict:
    """Load JSON file safely, return empty dict on error."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[!] Error loading {filepath}: {e}")
    return {}

def count_proxies(data: Dict) -> int:
    """Count proxies in data structure."""
    if isinstance(data.get('proxies'), list):
        return len(data['proxies'])
    return data.get('total_working', 0) or data.get('total_extracted', 0) or 0

def main():
    """Generate summary of all proxy data."""
    
    data_files = {
        'subscriptions': 'data/subscriptions_found.json',
        'telegram': 'data/tg_proxies_found.json',
        'http': 'data/http_proxies_found.json',
        'socks': 'data/socks_proxies_found.json',
        'utilities': 'data/utils_found.json',
    }
    
    summary = {
        'generated_at': datetime.now(timezone.utc).isoformat(),
        'categories': {},
        'total_proxies': 0,
    }
    
    for category, filepath in data_files.items():
        data = load_json_safe(filepath)
        count = count_proxies(data)
        
        summary['categories'][category] = {
            'count': count,
            'last_updated': data.get('generated_at', 'unknown'),
            'file': filepath
        }
        summary['total_proxies'] += count
    
    # Save summary
    output_file = 'data/summary.json'
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summary, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*50)
    print("REMAININGCONNECTIONS - Proxy Discovery Summary")
    print("="*50)
    print(f"\nGenerated: {summary['generated_at']}")
    print(f"\nTotal proxies: {summary['total_proxies']}")
    print("\nBy category:")
    
    for category, info in summary['categories'].items():
        print(f"  {category:15s}: {info['count']:5d} proxies")
    
    print("\n" + "="*50)
    print(f"Summary saved to: {output_file}")

if __name__ == '__main__':
    main()