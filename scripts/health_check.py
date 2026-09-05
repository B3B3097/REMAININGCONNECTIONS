 #!/usr/bin/env python3
"""
Health check for REMAININGCONNECTIONS system.
Monitors data freshness, workflow status, and proxy availability.
"""

import json
import os
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any

def load_json_safe(filepath: str) -> Dict:
    """Load JSON file safely."""
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except Exception as e:
        print(f"[!] Error loading {filepath}: {e}")
    return {}

def check_file_freshness(filepath: str, max_age_hours: int) -> Dict[str, Any]:
    """Check if file is fresh enough."""
    if not os.path.exists(filepath):
        return {
            'status': 'error',
            'message': 'File not found',
            'fresh': False
        }
    
    data = load_json_safe(filepath)
    generated_at = data.get('generated_at')
    
    if not generated_at:
        return {
            'status': 'warning',
            'message': 'No timestamp found',
            'fresh': False
        }
    
    try:
        # Parse ISO timestamp
        if generated_at.endswith('Z'):
            generated_at = generated_at[:-1] + '+00:00'
        
        timestamp = datetime.fromisoformat(generated_at)
        now = datetime.now(timezone.utc)
        age = now - timestamp
        
        fresh = age < timedelta(hours=max_age_hours)
        
        return {
            'status': 'ok' if fresh else 'warning',
            'message': f'Age: {age.total_seconds() / 3600:.1f}h',
            'fresh': fresh,
            'age_hours': age.total_seconds() / 3600,
            'last_update': generated_at
        }
    except Exception as e:
        return {
            'status': 'error',
            'message': f'Parse error: {e}',
            'fresh': False
        }

def check_proxy_availability(filepath: str, min_proxies: int) -> Dict[str, Any]:
    """Check if enough proxies are available."""
    data = load_json_safe(filepath)
    
    count = data.get('total_working', 0)
    if count == 0:
        count = len(data.get('proxies', []))
    
    sufficient = count >= min_proxies
    
    return {
        'status': 'ok' if sufficient else 'warning',
        'count': count,
        'minimum': min_proxies,
        'sufficient': sufficient
    }

def main():
    """Run health checks."""
    print("\n" + "="*60)
    print("REMAININGCONNECTIONS - System Health Check")
    print("="*60)
    print(f"\nTimestamp: {datetime.now(timezone.utc).isoformat()}\n")
    
    health_data = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'overall_status': 'ok',
        'checks': {}
    }
    
    # Define checks
    checks = {
        'subscriptions': {
            'file': 'data/subscriptions_found.json',
            'max_age_hours': 3,
            'min_proxies': 10
        },
        'telegram': {
            'file': 'data/tg_proxies_found.json',
            'max_age_hours': 3,
            'min_proxies': 5
        },
        'http': {
            'file': 'data/http_proxies_found.json',
            'max_age_hours': 6,
            'min_proxies': 10
        },
        'socks': {
            'file': 'data/socks_proxies_found.json',
            'max_age_hours': 6,
            'min_proxies': 5
        },
        'summary': {
            'file': 'data/summary.json',
            'max_age_hours': 12,
            'min_proxies': 0
        }
    }
    
    # Run checks
    for category, config in checks.items():
        print(f"[+] Checking {category}...")
        
        freshness = check_file_freshness(config['file'], config['max_age_hours'])
        availability = check_proxy_availability(config['file'], config['min_proxies'])
        
        health_data['checks'][category] = {
            'freshness': freshness,
            'availability': availability
        }
        
        # Print results
        fresh_icon = "✓" if freshness['fresh'] else "✗"
        avail_icon = "✓" if availability['sufficient'] else "✗"
        
        print(f"  {fresh_icon} Freshness: {freshness['message']}")
        print(f"  {avail_icon} Availability: {availability['count']} proxies")
        
        # Update overall status
        if freshness['status'] == 'error' or availability['status'] == 'error':
            health_data['overall_status'] = 'error'
        elif (freshness['status'] == 'warning' or availability['status'] == 'warning') and health_data['overall_status'] == 'ok':
            health_data['overall_status'] = 'warning'
    
    # Calculate summary statistics
    total_proxies = 0
    for category in ['subscriptions', 'telegram', 'http', 'socks']:
        if category in health_data['checks']:
            total_proxies += health_data['checks'][category]['availability']['count']
    
    health_data['total_proxies'] = total_proxies
    
    # Save health metrics
    os.makedirs('data', exist_ok=True)
    with open('data/health_metrics.json', 'w', encoding='utf-8') as f:
        json.dump(health_data, f, indent=2, ensure_ascii=False)
    
    # Print summary
    print("\n" + "="*60)
    print("Summary")
    print("="*60)
    print(f"Overall Status: {health_data['overall_status'].upper()}")
    print(f"Total Proxies: {total_proxies}")
    
    status_emoji = {
        'ok': '✅',
        'warning': '⚠️',
        'error': '❌'
    }
    
    print(f"\nStatus: {status_emoji.get(health_data['overall_status'], '❓')} {health_data['overall_status'].upper()}")
    print("\n" + "="*60)
    
    # Exit with appropriate code
    if health_data['overall_status'] == 'error':
        exit(1)
    elif health_data['overall_status'] == 'warning':
        exit(0)  # Don't fail on warnings
    else:
        exit(0)

if __name__ == '__main__':
    main()