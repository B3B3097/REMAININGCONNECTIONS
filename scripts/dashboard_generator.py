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
    http_data = load_json_safe('data/http_proxies_found.json', {"proxies": []})
    socks_data = load_json_safe('data/socks_proxies_found.json', {"proxies": []})
    utils_data = load_json_safe('data/utils_found.json', {"utilities": [], "summary": {}})
    health_data = load_json_safe('data/health_metrics.json', {})
    subs_data = load_json_safe('data/subscriptions_found.json', {"subscriptions": []})

    # Combine all proxies from different sources
    all_proxies = []
    all_proxies.extend(tg_data.get('proxies', []))
    all_proxies.extend(http_data.get('proxies', []))
    all_proxies.extend(socks_data.get('proxies', []))

    # Support both old 'working' field and new 'status' field
    working = [p for p in all_proxies if p.get('status') == 'working' or p.get('working', False)]
    total = len(all_proxies)
    working_count = len(working)

    print(f"[*] Total proxies: {total}")
    print(f"[*] Working proxies: {working_count}")

    # Build config data for embedding
    config_data = {
        "generated_at": datetime.datetime.utcnow().isoformat() + "Z",
        "total_proxies": total,
        "working_proxies": working_count,
        "proxies": all_proxies[:500],  # Limit to 500 for performance
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
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .card {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 0.5rem;
        }}
        .badge {{
            display: inline-block;
            padding: 0.15rem 0.5rem;
            border-radius: 9999px;
            font-size: 0.75rem;
            font-weight: 600;
        }}
        .badge-success {{ background: #065f46; color: #6ee7b7; }}
        .badge-warning {{ background: #78350f; color: #fde68a; }}
        .badge-danger {{ background: #7f1d1d; color: #fca5a5; }}
        .badge-neutral {{ background: #1e3a5f; color: #93c5fd; }}
        .badge-platform {{ background: #4c1d95; color: #c4b5fd; }}
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            padding: 0.5rem 1rem;
            border-radius: 0.375rem;
            font-size: 0.875rem;
            font-weight: 500;
            text-decoration: none;
            cursor: pointer;
            border: none;
            transition: opacity 0.2s;
        }}
        .btn:hover {{ opacity: 0.85; }}
        .btn-primary {{ background: #2563eb; color: white; }}
        .btn-secondary {{ background: #374151; color: #d1d5db; }}
        .ping-dot {{
            display: inline-block;
            width: 8px;
            height: 8px;
            border-radius: 50%;
            margin-right: 4px;
        }}
        .ping-good {{ background: #10b981; }}
        .ping-ok {{ background: #f59e0b; }}
        .ping-bad {{ background: #ef4444; }}
        .text-muted {{ color: #94a3b8; }}
        .text-faint {{ color: #64748b; }}
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">
    <div class="container mx-auto px-4 py-8 max-w-7xl">
        <header class="mb-8">
            <h1 class="text-4xl font-bold mb-2">REMAININGCONNECTIONS</h1>
            <p class="text-slate-400">Proxy Discovery & Monitoring Dashboard</p>
        </header>

        <!-- Stats Overview -->
        <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div class="card p-6">
                <div class="text-sm text-muted mb-1">Total Proxies</div>
                <div class="text-3xl font-bold" id="stat-total">0</div>
            </div>
            <div class="card p-6">
                <div class="text-sm text-muted mb-1">Working Proxies</div>
                <div class="text-3xl font-bold text-green-400" id="stat-working">0</div>
            </div>
            <div class="card p-6">
                <div class="text-sm text-muted mb-1">Success Rate</div>
                <div class="text-3xl font-bold text-blue-400" id="stat-rate">0%</div>
            </div>
            <div class="card p-6">
                <div class="text-sm text-muted mb-1">Last Update</div>
                <div class="text-sm font-medium text-slate-300" id="stat-updated">Never</div>
            </div>
        </div>

        <!-- Filters -->
        <div class="card p-4 mb-6">
            <div class="flex flex-wrap gap-3 items-center">
                <span class="text-sm text-muted">Filter:</span>
                <button class="btn btn-secondary btn-sm filter-btn active" data-filter="all">All</button>
                <button class="btn btn-secondary btn-sm filter-btn" data-filter="working">Working</button>
                <button class="btn btn-secondary btn-sm filter-btn" data-filter="http">HTTP</button>
                <button class="btn btn-secondary btn-sm filter-btn" data-filter="https">HTTPS</button>
                <button class="btn btn-secondary btn-sm filter-btn" data-filter="socks4">SOCKS4</button>
                <button class="btn btn-secondary btn-sm filter-btn" data-filter="socks5">SOCKS5</button>
                <input type="text" id="search-input" placeholder="Search by host, port, country..." 
                       class="ml-auto px-3 py-2 bg-slate-800 border border-slate-600 rounded text-sm focus:outline-none focus:border-blue-500">
            </div>
        </div>

        <!-- Proxy List -->
        <div class="card p-6">
            <h2 class="text-xl font-semibold mb-4">Proxy List</h2>
            <div id="proxy-container" class="space-y-3">
                <!-- Proxies will be inserted here by JS -->
            </div>
            <div id="no-results" class="text-center py-8 text-slate-400 hidden">
                No proxies found matching your criteria.
            </div>
        </div>

        <footer class="mt-8 text-center text-sm text-faint">
            <p>Generated by REMAININGCONNECTIONS | <a href="https://t.me/REMAININGCONNECTIONS" class="text-blue-400 hover:underline" target="_blank">Telegram Channel</a></p>
        </footer>
    </div>

    <script>
        const CONFIG = {safe_json};

        let currentFilter = 'all';
        let searchQuery = '';

        function formatDate(isoString) {{
            const date = new Date(isoString);
            return date.toLocaleString('en-US', {{ 
                year: 'numeric', 
                month: 'short', 
                day: 'numeric',
                hour: '2-digit',
                minute: '2-digit'
            }});
        }}

        function renderStats() {{
            document.getElementById('stat-total').textContent = CONFIG.total_proxies.toLocaleString();
            document.getElementById('stat-working').textContent = CONFIG.working_proxies.toLocaleString();
            
            const rate = CONFIG.total_proxies > 0 
                ? ((CONFIG.working_proxies / CONFIG.total_proxies) * 100).toFixed(1)
                : 0;
            document.getElementById('stat-rate').textContent = rate + '%';
            
            document.getElementById('stat-updated').textContent = formatDate(CONFIG.generated_at);
        }}

        function matchesFilter(proxy) {{
            if (currentFilter === 'all') return true;
            if (currentFilter === 'working') {{
                return proxy.status === 'working' || proxy.working === true;
            }}
            const protocol = (proxy.protocol || proxy.type || '').toLowerCase();
            return protocol === currentFilter;
        }}

        function matchesSearch(proxy) {{
            if (!searchQuery) return true;
            const query = searchQuery.toLowerCase();
            const searchable = [
                proxy.host || '',
                String(proxy.port || ''),
                proxy.country || '',
                proxy.protocol || proxy.type || '',
                proxy.source || ''
            ].join(' ').toLowerCase();
            return searchable.includes(query);
        }}

        function getStatusBadge(proxy) {{
            const status = proxy.status || (proxy.working ? 'working' : 'unknown');
            const badges = {{
                'working': '<span class="badge badge-success">✓ Working</span>',
                'failed': '<span class="badge badge-danger">✗ Failed</span>',
                'timeout': '<span class="badge badge-warning">⏱ Timeout</span>',
                'unknown': '<span class="badge badge-neutral">? Unknown</span>'
            }};
            return badges[status] || badges.unknown;
        }}

        function getPingIndicator(ping) {{
            if (!ping) return '';
            let dotClass = 'ping-bad';
            if (ping < 200) dotClass = 'ping-good';
            else if (ping < 500) dotClass = 'ping-ok';
            return `<span class="ping-dot ${{dotClass}}"></span>${{ping}}ms`;
        }}

        function renderProxies() {{
            const container = document.getElementById('proxy-container');
            const noResults = document.getElementById('no-results');
            
            const filtered = CONFIG.proxies.filter(p => matchesFilter(p) && matchesSearch(p));
            
            if (filtered.length === 0) {{
                container.innerHTML = '';
                noResults.classList.remove('hidden');
                return;
            }}
            
            noResults.classList.add('hidden');
            container.innerHTML = filtered.map(proxy => {{
                const protocol = (proxy.protocol || proxy.type || 'unknown').toUpperCase();
                const lastChecked = proxy.last_checked 
                    ? `<span class="text-xs text-faint">Checked: ${{formatDate(proxy.last_checked)}}</span>`
                    : '';
                const ping = proxy.ping ? getPingIndicator(proxy.ping) : '';
                const country = proxy.country ? `<span class="badge badge-platform">${{proxy.country}}</span>` : '';
                const source = proxy.source ? `<span class="text-xs text-faint">via ${{proxy.source}}</span>` : '';
                
                return `
                    <div class="border border-slate-700 rounded p-4 hover:border-slate-600 transition-colors">
                        <div class="flex flex-wrap items-center gap-2 mb-2">
                            <span class="font-mono text-lg font-semibold">${{proxy.host}}:${{proxy.port}}</span>
                            <span class="badge badge-platform">${{protocol}}</span>
                            ${{country}}
                            ${{getStatusBadge(proxy)}}
                        </div>
                        <div class="flex flex-wrap gap-4 text-sm text-slate-400">
                            ${{ping ? `<span>${{ping}}</span>` : ''}}
                            ${{lastChecked}}
                            ${{source}}
                        </div>
                    </div>
                `;
            }}).join('');
        }}

        // Event listeners
        document.querySelectorAll('.filter-btn').forEach(btn => {{
            btn.addEventListener('click', () => {{
                document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
                btn.classList.add('active');
                currentFilter = btn.dataset.filter;
                renderProxies();
            }});
        }});

        document.getElementById('search-input').addEventListener('input', (e) => {{
            searchQuery = e.target.value;
            renderProxies();
        }});

        // Initial render
        renderStats();
        renderProxies();
    </script>
</body>
</html>"""

    output_path = os.path.join('docs', 'index.html')
    os.makedirs('docs', exist_ok=True)

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_template)

    print(f"[✓] Dashboard generated: {output_path}")
    print(f"[✓] Total: {total}, Working: {working_count}")


if __name__ == "__main__":
    try:
        generate_dashboard()
        sys.exit(0)
    except Exception as e:
        print(f"[!] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)