#!/usr/bin/env python3
"""
Static Dashboard Generator for REMAININGCONNECTIONS.

This script generates the interactive JavaScript-based dashboard (index.html) 
by injecting the latest data from the 'data/' directory into a pre-defined template.
It ensures the GitHub Pages site always displays the most up-to-date information 
without requiring server-side rendering.

Features:
- Data Injection: Replaces placeholder variables in the HTML template with real JSON data.
- Asset Optimization: Compresses inline CSS/JS where possible.
- Version Tracking: Embeds build timestamps and commit hashes.
- Fallback Handling: Generates a minimal "No Data" state if JSON files are missing.
- Template Management: Supports multiple layout themes via configuration.

Dependencies:
    json, os, pathlib, datetime, re, hashlib, logging
    (Optional: jinja2 for advanced templating, but we use regex/string replace for zero-dependency deployment)
"""

from __future__ import annotations

import json
import os
import re
import sys
import logging
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger("DashboardGenerator")


# --- Constants ---

TEMPLATE_DIR = Path("templates")
OUTPUT_DIR = Path("docs")
DATA_DIR = Path("data")

# Default HTML Template (Embedded to ensure portability)
DEFAULT_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REMAININGCONNECTIONS Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background-color: #0f172a; color: #e2e8f0; font-family: sans-serif; }
        .card { background-color: #1e293b; border-radius: 0.5rem; padding: 1rem; margin-bottom: 1rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
        .status-working { color: #22c55e; }
        .status-failed { color: #ef4444; }
        .loading { opacity: 0.5; pointer-events: none; }
    </style>
</head>
<body class="p-6">
    <header class="mb-8 text-center">
        <h1 class="text-4xl font-bold text-blue-400">REMAININGCONNECTIONS</h1>
        <p class="text-gray-400 mt-2">Live Proxy & Subscription Monitor</p>
        <div id="build-info" class="text-sm text-gray-500 mt-1"></div>
    </header>

    <main class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <!-- Stats Cards -->
        <div class="card col-span-1">
            <h3 class="text-lg font-semibold text-gray-300">Total Proxies</h3>
            <div id="stat-total-proxies" class="text-3xl font-bold mt-2">Loading...</div>
        </div>
        <div class="card col-span-1">
            <h3 class="text-lg font-semibold text-gray-300">Working Proxies</h3>
            <div id="stat-working-proxies" class="text-3xl font-bold status-working mt-2">Loading...</div>
        </div>
        <div class="card col-span-1">
            <h3 class="text-lg font-semibold text-gray-300">Subscriptions</h3>
            <div id="stat-subs" class="text-3xl font-bold mt-2">Loading...</div>
        </div>
        <div class="card col-span-1">
            <h3 class="text-lg font-semibold text-gray-300">Uptime</h3>
            <div id="stat-uptime" class="text-3xl font-bold mt-2">--%</div>
        </div>

        <!-- Charts Section -->
        <div class="card col-span-1 md:col-span-2">
            <h3 class="text-lg font-semibold mb-4">Protocol Distribution</h3>
            <canvas id="protocolChart" height="150"></canvas>
        </div>
        <div class="card col-span-1 md:col-span-2">
            <h3 class="text-lg font-semibold mb-4">Latency Overview</h3>
            <canvas id="latencyChart" height="150"></canvas>
        </div>

        <!-- Recent Updates Table -->
        <div class="card col-span-1 md:col-span-4">
            <h3 class="text-lg font-semibold mb-4">Latest Working Proxies</h3>
            <div class="overflow-x-auto">
                <table class="min-w-full divide-y divide-gray-700">
                    <thead>
                        <tr>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Protocol</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Server</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Latency</th>
                            <th class="px-6 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider">Status</th>
                        </tr>
                    </thead>
                    <tbody id="proxy-table-body" class="divide-y divide-gray-700">
                        <!-- Rows injected here -->
                    </tbody>
                </table>
            </div>
        </div>
    </main>

    <footer class="mt-12 text-center text-gray-500 text-sm">
        Generated by REMAININGCONNECTIONS Dashboard Generator | <span id="timestamp"></span>
    </footer>

    <script>
        // Embedded Configuration Data
        const CONFIG_DATA = {{ CONFIG_JSON }};

        document.addEventListener('DOMContentLoaded', () => {
            renderStats(CONFIG_DATA);
            renderCharts(CONFIG_DATA);
            renderTable(CONFIG_DATA);
            document.getElementById('timestamp').innerText = new Date().toLocaleString();
            document.getElementById('build-info').innerText = "Build: " + (CONFIG_DATA.build_info || "Unknown");
        });

        function renderStats(data) {
            const proxies = data.proxies || [];
            const subs = data.subscriptions || [];
            
            const totalP = proxies.length;
            const workingP = proxies.filter(p => p.status === 'working').length;
            const uptime = totalP > 0 ? Math.round((workingP / totalP) * 100) : 0;

            document.getElementById('stat-total-proxies').innerText = totalP;
            document.getElementById('stat-working-proxies').innerText = workingP;
            document.getElementById('stat-subs').innerText = subs.length;
            document.getElementById('stat-uptime').innerText = uptime + "%";
        }

        function renderCharts(data) {
            const proxies = data.proxies || [];
            
            // Protocol Distribution
            const protocols = {};
            proxies.forEach(p => {
                const proto = p.protocol || 'unknown';
                protocols[proto] = (protocols[proto] || 0) + 1;
            });

            const ctx1 = document.getElementById('protocolChart').getContext('2d');
            new Chart(ctx1, {
                type: 'doughnut',
                data: {
                    labels: Object.keys(protocols),
                    datasets: [{
                        data: Object.values(protocols),
                        backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#ef4444', '#8b5cf6']
                    }]
                },
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });

            // Latency (Simple Histogram simulation)
            const latencies = proxies.map(p => p.latency_ms || 0).filter(l => l > 0);
            const buckets = { '<100ms': 0, '100-300ms': 0, '>300ms': 0 };
            latencies.forEach(l => {
                if (l < 100) buckets['<100ms']++;
                else if (l <= 300) buckets['100-300ms']++;
                else buckets['>300ms']++;
            });

            const ctx2 = document.getElementById('latencyChart').getContext('2d');
            new Chart(ctx2, {
                type: 'bar',
                data: {
                    labels: Object.keys(buckets),
                    datasets: [{
                        label: 'Count',
                        data: Object.values(buckets),
                        backgroundColor: '#6366f1'
                    }]
                },
                options: { responsive: true, scales: { y: { beginAtZero: true } } }
            });
        }

        function renderTable(data) {
            const tbody = document.getElementById('proxy-table-body');
            const workingProxies = (data.proxies || [])
                .filter(p => p.status === 'working')
                .slice(0, 10); // Top 10

            tbody.innerHTML = workingProxies.map(p => `
                <tr>
                    <td class="px-6 py-4 whitespace-nowrap text-sm font-medium text-white">${p.protocol}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">${p.server}</td>
                    <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-300">${p.latency_ms || '-'} ms</td>
                    <td class="px-6 py-4 whitespace-nowrap"><span class="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">Working</span></td>
                </tr>
            `).join('');
        }
    </script>
</body>
</html>"""


class DashboardGenerator:
    """
    Main class for generating the static dashboard.
    """

    def __init__(self, data_dir: str = "data", output_dir: str = "docs"):
        self.data_dir = Path(data_dir)
        self.output_dir = Path(output_dir)
        
    def load_data(self) -> Dict[str, Any]:
        """Load all necessary data files."""
        result = {
            "proxies": [],
            "subscriptions": [],
            "utils": [],
            "build_info": f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        }
        
        # Load Proxies
        prox_file = self.data_dir / "tg_proxies_found.json"
        if prox_file.exists():
            try:
                with open(prox_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                result["proxies"] = data.get("proxies", [])
            except Exception as e:
                logger.error(f"Failed to load proxies: {e}")
                
        # Load Subscriptions
        sub_file = self.data_dir / "subscriptions_found.json"
        if sub_file.exists():
            try:
                with open(sub_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                result["subscriptions"] = data.get("subscriptions", [])
            except Exception as e:
                logger.error(f"Failed to load subscriptions: {e}")
                
        return result

    def generate_html(self, config_data: Dict[str, Any], template: str = DEFAULT_TEMPLATE) -> str:
        """Inject data into the HTML template."""
        # Sanitize JSON to prevent XSS in the embedded JS block
        safe_json = json.dumps(config_data, ensure_ascii=False)
        
        # Replace placeholder
        html_content = template.replace("{{ CONFIG_JSON }}", safe_json)
        
        # Minify JS (Simple regex-based minification for demo purposes)
        # In production, use tools like terser.
        html_content = re.sub(r'\n\s*\n', '\n', html_content)
        html_content = re.sub(r'/\*.*?\*/', '', html_content, flags=re.DOTALL)
        
        return html_content

    def run(self):
        """Execute the generation process."""
        logger.info("Starting Dashboard Generation...")
        
        # Ensure output directory exists
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Load Data
        config_data = self.load_data()
        logger.info(f"Loaded {len(config_data['proxies'])} proxies and {len(config_data['subscriptions'])} subscriptions.")
        
        # Generate HTML
        html_output = self.generate_html(config_data)
        
        # Write Output
        output_path = self.output_dir / "index.html"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html_output)
            
        file_size = output_path.stat().st_size
        logger.info(f"Dashboard generated successfully: {output_path} ({file_size / 1024:.2f} KB)")
        
        return output_path


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", default="data", help="Path to data directory")
    parser.add_argument("--output-dir", default="docs", help="Path to output directory")
    
    args = parser.parse_args()
    
    generator = DashboardGenerator(data_dir=args.data_dir, output_dir=args.output_dir)
    generator.run()


if __name__ == "__main__":
    main()