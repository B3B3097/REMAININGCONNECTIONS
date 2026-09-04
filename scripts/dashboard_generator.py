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
    working = [p for p in proxies if p.get('working', False)]
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
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">
    <div class="container mx-auto px-4 py-8">
        <header class="mb-8">
            <h1 class="text-3xl font-bold text-blue-400">REMAININGCONNECTIONS</h1>
            <p class="text-slate-400 mt-1">Proxy Discovery &amp; Validation Dashboard</p>
            <p class="text-slate-500 text-sm mt-1" id="generated-at"></p>
        </header>

        <!-- Stats Cards -->
        <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
            <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h3 class="text-slate-400 text-sm font-medium">Total Proxies</h3>
                <p class="text-3xl font-bold text-white mt-2" id="stat-total">-</p>
            </div>
            <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h3 class="text-slate-400 text-sm font-medium">Working</h3>
                <p class="text-3xl font-bold text-green-400 mt-2" id="stat-working">-</p>
            </div>
            <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h3 class="text-slate-400 text-sm font-medium">Success Rate</h3>
                <p class="text-3xl font-bold text-blue-400 mt-2" id="stat-rate">-</p>
            </div>
            <div class="bg-slate-800 rounded-lg p-6 border border-slate-700">
                <h3 class="text-slate-400 text-sm font-medium">Subscriptions</h3>
                <p class="text-3xl font-bold text-purple-400 mt-2" id="stat-subs">-</p>
            </div>
        </div>

        <!-- Chart -->
        <div class="bg-slate-800 rounded-lg p-6 border border-slate-700 mb-8">
            <h2 class="text-xl font-bold mb-4">Protocol Distribution</h2>
            <canvas id="protocolChart" height="80"></canvas>
        </div>

        <!-- Proxy Table -->
        <div class="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
            <div class="p-4 border-b border-slate-700">
                <h2 class="text-xl font-bold">Working Proxies</h2>
            </div>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-slate-700">
                    <thead class="bg-slate-700">
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase">Protocol</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase">Server</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase">Latency</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase">Score</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-slate-300 uppercase">TLS Cipher</th>
                        </tr>
                    </thead>
                    <tbody id="proxy-table-body" class="divide-y divide-slate-700">
                    </tbody>
                </table>
            </div>
        </div>

        <footer class="mt-8 text-center text-slate-500 text-sm">
            <p>REMAININGCONNECTIONS &copy; 2024 | Auto-generated dashboard</p>
        </footer>
    </div>

    <script>
        function escapeHtml(text) {
            const map = {
                '&': '&amp;',
                '<': '&lt;',
                '>': '&gt;',
                '"': '&quot;',
                "'": '&#039;'
            };
            return String(text).replace(/[&<>"']/g, function(m) { return map[m]; });
        }

        function getScoreColor(score) {
            if (score == null) return 'bg-slate-600 text-slate-300';
            if (score >= 80) return 'bg-green-800 text-green-200';
            if (score >= 50) return 'bg-yellow-800 text-yellow-200';
            return 'bg-red-800 text-red-200';
        }

        // Embedded Configuration Data
        const CONFIG_DATA_STR = '__CONFIG_JSON__';
        let CONFIG_DATA;
        try {
            CONFIG_DATA = JSON.parse(CONFIG_DATA_STR);
        } catch (e) {
            console.error("Failed to parse config data", e);
            CONFIG_DATA = {};
        }

        // Render stats
        document.getElementById('stat-total').textContent = CONFIG_DATA.total_proxies || 0;
        document.getElementById('stat-working').textContent = CONFIG_DATA.working_proxies || 0;
        const rate = CONFIG_DATA.total_proxies > 0
            ? ((CONFIG_DATA.working_proxies / CONFIG_DATA.total_proxies) * 100).toFixed(1) + '%'
            : '0%';
        document.getElementById('stat-rate').textContent = rate;
        document.getElementById('stat-subs').textContent = CONFIG_DATA.subscriptions_count || 0;
        document.getElementById('generated-at').textContent = 'Generated: ' + (CONFIG_DATA.generated_at || 'unknown');

        // Render protocol chart
        if (CONFIG_DATA.proxies && CONFIG_DATA.proxies.length > 0) {
            const protocolCounts = {};
            CONFIG_DATA.proxies.forEach(p => {
                const proto = p.protocol || 'unknown';
                protocolCounts[proto] = (protocolCounts[proto] || 0) + 1;
            });
            const ctx = document.getElementById('protocolChart').getContext('2d');
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: Object.keys(protocolCounts),
                    datasets: [{
                        label: 'Proxies by Protocol',
                        data: Object.values(protocolCounts),
                        backgroundColor: [
                            'rgba(59,130,246,0.7)',
                            'rgba(16,185,129,0.7)',
                            'rgba(245,158,11,0.7)',
                            'rgba(239,68,68,0.7)',
                            'rgba(139,92,246,0.7)',
                            'rgba(236,72,153,0.7)'
                        ],
                        borderColor: [
                            'rgba(59,130,246,1)',
                            'rgba(16,185,129,1)',
                            'rgba(245,158,11,1)',
                            'rgba(239,68,68,1)',
                            'rgba(139,92,246,1)',
                            'rgba(236,72,153,1)'
                        ],
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    plugins: {
                        legend: { labels: { color: '#e2e8f0' } }
                    },
                    scales: {
                        x: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } },
                        y: { ticks: { color: '#94a3b8' }, grid: { color: '#334155' } }
                    }
                }
            });
        }

        // Render proxy table
        function renderTable(data) {
            const tbody = document.getElementById('proxy-table-body');
            const workingProxies = (data.proxies || []).filter(p => p.working);

            if (workingProxies.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" class="px-6 py-4 text-center text-slate-400">No working proxies found.</td></tr>';
                return;
            }

            tbody.innerHTML = workingProxies.map(p => {
                const latency = p.tcp_latency_ms ? p.tcp_latency_ms.toFixed(0) + ' ms'
                    : (p.latency_ms ? p.latency_ms.toFixed(0) + ' ms' : '-');
                const score = p.deep_score != null ? p.deep_score.toFixed(1) : '-';
                const cipher = p.tls_cipher || '-';
                return '<tr>'
                    + '<td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-blue-300">' + escapeHtml(p.protocol || '') + '</td>'
                    + '<td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300 font-mono">' + escapeHtml(p.server || '') + '</td>'
                    + '<td class="px-6 py-4 whitespace-nowrap text-sm text-slate-300">' + escapeHtml(latency) + '</td>'
                    + '<td class="px-6 py-4 whitespace-nowrap text-sm">'
                    +   '<span class="px-2 py-1 rounded text-xs font-bold ' + getScoreColor(p.deep_score) + '">' + escapeHtml(score) + '</span>'
                    + '</td>'
                    + '<td class="px-6 py-4 whitespace-nowrap text-xs text-slate-400 font-mono truncate" style="max-width:150px" title="' + escapeHtml(cipher) + '">' + escapeHtml(cipher) + '</td>'
                    + '</tr>';
            }).join('');
        }

        renderTable(CONFIG_DATA);
    </script>
</body>
</html>"""

    # Inject the JSON data safely
    escaped_json = safe_json.replace("'", "\\'")
    html_output = html_template.replace('__CONFIG_JSON__', escaped_json)

    # Write output
    os.makedirs('docs', exist_ok=True)
    output_path = os.path.join('docs', 'index.html')
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_output)

    print(f"[+] Dashboard generated: {output_path}")
    print(f"[+] Total proxies: {total}, Working: {working_count}")


if __name__ == '__main__':
    generate_dashboard()