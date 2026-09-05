 #!/usr/bin/env python3
"""
Export proxies to various formats (plain text, CSV, etc.)
"""

import json
import csv
import os
import sys
from typing import List, Dict

def load_proxies(filepath: str) -> List[Dict]:
    """Load proxies from JSON file."""
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data.get('proxies', [])
    except Exception as e:
        print(f"[!] Error loading {filepath}: {e}")
        return []

def export_to_txt(proxies: List[Dict], output: str, format_type: str = 'simple'):
    """Export proxies to plain text file."""
    with open(output, 'w', encoding='utf-8') as f:
        for proxy in proxies:
            host = proxy.get('host')
            port = proxy.get('port')
            protocol = proxy.get('protocol', '')
            
            if format_type == 'simple':
                # host:port
                f.write(f"{host}:{port}\n")
            elif format_type == 'protocol':
                # protocol://host:port
                f.write(f"{protocol}://{host}:{port}\n")
            elif format_type == 'detailed':
                # host:port | protocol | latency
                latency = proxy.get('latency_ms', 'N/A')
                f.write(f"{host}:{port} | {protocol} | {latency}ms\n")

def export_to_csv(proxies: List[Dict], output: str):
    """Export proxies to CSV file."""
    if not proxies:
        return
    
    fieldnames = ['host', 'port', 'protocol', 'type', 'latency_ms', 'verified_at', 'source']
    
    with open(output, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
        writer.writeheader()
        writer.writerows(proxies)

def export_telegram_links(proxies: List[Dict], output: str):
    """Export Telegram proxy links."""
    with open(output, 'w', encoding='utf-8') as f:
        for proxy in proxies:
            if 'tg_link' in proxy:
                f.write(f"{proxy['tg_link']}\n")

def export_pac_file(proxies: List[Dict], output: str):
    """Export PAC (Proxy Auto-Config) file."""
    # Simple PAC that rotates through proxies
    pac_content = '''function FindProxyForURL(url, host) {
    // Proxy list
    var proxies = [
'''
    
    for proxy in proxies:
        protocol = proxy.get('protocol', 'http').upper()
        if protocol in ['HTTP', 'HTTPS']:
            pac_content += f'        "PROXY {proxy["host"]}:{proxy["port"]}",\n'
        elif protocol.startswith('SOCKS'):
            socks_version = 'SOCKS5' if '5' in protocol else 'SOCKS'
            pac_content += f'        "{socks_version} {proxy["host"]}:{proxy["port"]}",\n'
    
    pac_content += '''    ];
    
    // Round-robin selection
    var proxy = proxies[Math.floor(Math.random() * proxies.length)];
    return proxy + "; DIRECT";
}
'''
    
    with open(output, 'w', encoding='utf-8') as f:
        f.write(pac_content)

def main():
    """Export all data formats."""
    os.makedirs('exports', exist_ok=True)
    
    data_files = {
        'http': 'data/http_proxies_found.json',
        'socks': 'data/socks_proxies_found.json',
        'telegram': 'data/tg_proxies_found.json',
    }
    
    print("[+] Exporting proxy data to multiple formats...")
    
    for category, filepath in data_files.items():
        if not os.path.exists(filepath):
            print(f"[!] Skipping {category}: file not found")
            continue
        
        proxies = load_proxies(filepath)
        if not proxies:
            print(f"[!] No proxies in {category}")
            continue
        
        print(f"\n[+] Exporting {len(proxies)} {category} proxies...")
        
        # Plain text formats
        export_to_txt(proxies, f'exports/{category}_simple.txt', 'simple')
        print(f"    ✓ exports/{category}_simple.txt")
        
        export_to_txt(proxies, f'exports/{category}_protocol.txt', 'protocol')
        print(f"    ✓ exports/{category}_protocol.txt")
        
        export_to_txt(proxies, f'exports/{category}_detailed.txt', 'detailed')
        print(f"    ✓ exports/{category}_detailed.txt")
        
        # CSV format
        export_to_csv(proxies, f'exports/{category}_proxies.csv')
        print(f"    ✓ exports/{category}_proxies.csv")
        
        # Special formats
        if category == 'telegram':
            export_telegram_links(proxies, 'exports/telegram_links.txt')
            print(f"    ✓ exports/telegram_links.txt")
        
        if category in ['http', 'socks']:
            export_pac_file(proxies, f'exports/{category}_proxy.pac')
            print(f"    ✓ exports/{category}_proxy.pac")
    
    # Combined exports
    all_http = load_proxies('data/http_proxies_found.json')
    all_socks = load_proxies('data/socks_proxies_found.json')
    all_combined = all_http + all_socks
    
    if all_combined:
        print(f"\n[+] Exporting {len(all_combined)} combined proxies...")
        export_to_txt(all_combined, 'exports/all_proxies.txt', 'simple')
        print(f"    ✓ exports/all_proxies.txt")
        
        export_to_csv(all_combined, 'exports/all_proxies.csv')
        print(f"    ✓ exports/all_proxies.csv")
        
        export_pac_file(all_combined, 'exports/all_proxies.pac')
        print(f"    ✓ exports/all_proxies.pac")
    
    print("\n[+] Export complete!")

if __name__ == '__main__':
    main()