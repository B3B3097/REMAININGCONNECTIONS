#!/usr/bin/env python3
"""
Dashboard Generator for REMAININGCONNECTIONS
Generates a static HTML dashboard from proxy data files.
"""

import json
import os
import sys
import datetime


def load_json_safe(filepath, default=None):
    """Load JSON file safely, return default on failure."""
    if default is None:
        default = {}
    try:
        if os.path.exists(filepath):
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"[!] Error loading {filepath}: {e}")
    return default


def generate_dashboard():
    """Generate the static HTML dashboard."""
    print("[*] Starting dashboard generation...")

    # Load data files
    tg_data = load_json_safe('data/tg_proxies_found.json', {"proxies": []})
    utils_data = load_json_safe('data/utils_found.json', {"utilities": [], "summary": {}})
    health_data = load_json_safe('data/health_metrics.json', {})
    subs_data = load_json_safe('data/subscriptions_found.json', {"subscriptions": []})

    proxies = tg_data.get('proxies', [])
    # Support both old 'working' field and new 'status' field
    working = [p for p in proxies if p.get('status') == 'working' or p.get('working', False)]
    total = len(proxies)
    working_count = len(working)

    # Build config data for embedding
    config_data = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "total_proxies": total,
        "working_proxies": working_count,
        "proxies": proxies[:500],
        "utilities_summary": utils_data.get('summary', {}),
        "subscriptions_count": len(subs_data.get('subscriptions', [])),
    }

    # Sanitize JSON for embedding in JS
    safe_json = json.dumps(config_data, ensure_ascii=False)
    safe_json = safe_json.replace('</script>', '<\\/script>')

    html_template = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REMAININGCONNECTIONS Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: #fff;
            min-height: 100vh;
            padding: 2rem;
        }
        .container {
            max-width: 1400px;
            margin: 0 auto;
        }
        header {
            text-align: center;
            margin-bottom: 3rem;
        }
        h1 {
            font-size: 3rem;
            margin-bottom: 0.5rem;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }
        .subtitle {
            font-size: 1.2rem;
            opacity: 0.9;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 1.5rem;
            margin-bottom: 3rem;
        }
        .stat-card {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 1rem;
            padding: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            transition: transform 0.3s ease;
        }
        .stat-card:hover {
            transform: translateY(-5px);
        }
        .stat-value {
            font-size: 2.5rem;
            font-weight: bold;
            margin: 0.5rem 0;
        }
        .stat-label {
            font-size: 0.9rem;
            opacity: 0.8;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .proxy-table {
            background: rgba(255, 255, 255, 0.1);
            backdrop-filter: blur(10px);
            border-radius: 1rem;
            padding: 2rem;
            border: 1px solid rgba(255, 255, 255, 0.2);
            overflow-x: auto;
        }
        table {
            width: 100%;
            border-collapse: collapse;
        }
        th, td {
            padding: 1rem;
            text-align: left;
            border-bottom: 1px solid rgba(255, 255, 255, 0.1);
        }
        th {
            font-weight: 600;
            background: rgba(255, 255, 255, 0.1);
        }
        tr:hover {
            background: rgba(255, 255, 255, 0.05);
        }
        .status-badge {
            display: inline-block;
            padding: 0.25rem 0.75rem;
            border-radius: 1rem;
            font-size: 0.85rem;
            font-weight: 500;
        }
        .status-working {
            background: rgba(34, 197, 94, 0.3);
            border: 1px solid rgba(34, 197, 94, 0.5);
        }
        .status-unknown {
            background: rgba(251, 191, 36, 0.3);
            border: 1px solid rgba(251, 191, 36, 0.5);
        }
        footer {
            text-align: center;
            margin-top: 3rem;
            opacity: 0.8;
            font-size: 0.9rem;
        }
        .timestamp {
            margin-top: 1rem;
            font-style: italic;
        }
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🌐 REMAININGCONNECTIONS</h1>
            <p class="subtitle">Proxy & Subscription Discovery Dashboard</p>
        </header>
        
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-label">Total Proxies</div>
                <div class="stat-value" id="total-proxies">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Working Proxies</div>
                <div class="stat-value" id="working-proxies">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Subscriptions</div>
                <div class="stat-value" id="subscriptions">0</div>
            </div>
            <div class="stat-card">
                <div class="stat-label">Success Rate</div>
                <div class="stat-value" id="success-rate">0%</div>
            </div>
        </div>
        
        <div class="proxy-table">
            <h2>Recent Proxies (Top 100)</h2>
            <table>
                <thead>
                    <tr>
                        <th>Server</th>
                        <th>Port</th>
                        <th>Protocol</th>
                        <th>Status</th>
                    </tr>
                </thead>
                <tbody id="proxy-list">
                    <tr><td colspan="4" style="text-align: center;">Loading...</td></tr>
                </tbody>
            </table>
        </div>
        
        <footer>
            <p>Automated proxy and subscription discovery system</p>
            <p class="timestamp" id="last-updated">Last updated: Loading...</p>
            <p>⭐ <a href="https://github.com/B3B3097/REMAININGCONNECTIONS" style="color: #fff;">GitHub Repository</a></p>
        </footer>
    </div>

    <script>
        const data = """ + safe_json + """;
        
        // Update stats
        document.getElementById('total-proxies').textContent = data.total_proxies.toLocaleString();
        document.getElementById('working-proxies').textContent = data.working_proxies.toLocaleString();
        document.getElementById('subscriptions').textContent = data.subscriptions_count.toLocaleString();
        
        const successRate = data.total_proxies > 0 
            ? ((data.working_proxies / data.total_proxies) * 100).toFixed(1) 
            : 0;
        document.getElementById('success-rate').textContent = successRate + '%';
        
        // Update timestamp
        const timestamp = new Date(data.generated_at);
        document.getElementById('last-updated').textContent = 
            'Last updated: ' + timestamp.toUTCString();
        
        // Populate proxy table
        const tbody = document.getElementById('proxy-list');
        tbody.innerHTML = '';
        
        const proxies = data.proxies.slice(0, 100);
        if (proxies.length === 0) {
            tbody.innerHTML = '<tr><td colspan="4" style="text-align: center;">No proxies available</td></tr>';
        } else {
            proxies.forEach(proxy => {
                const row = document.createElement('tr');
                
                const status = proxy.status || (proxy.working ? 'working' : 'unknown');
                const statusClass = status === 'working' ? 'status-working' : 'status-unknown';
                
                row.innerHTML = `
                    <td>${proxy.server || 'N/A'}</td>
                    <td>${proxy.port || 'N/A'}</td>
                    <td>${proxy.protocol || 'N/A'}</td>
                    <td><span class="status-badge ${statusClass}">${status}</span></td>
                `;
                
                tbody.appendChild(row);
            });
        }
    </script>
</body>
</html>"""

    # Write the dashboard
    output_path = 'docs/index.html'
    os.makedirs('docs', exist_ok=True)
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)

    print(f"[✓] Dashboard generated successfully: {output_path}")
    print(f"    Total proxies: {total}")
    print(f"    Working proxies: {working_count}")
    print(f"    Subscriptions: {len(subs_data.get('subscriptions', []))}")
    return True


if __name__ == "__main__":
    try:
        success = generate_dashboard()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"[✗] Dashboard generation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)