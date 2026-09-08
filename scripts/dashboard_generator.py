#!/usr/bin/env python3
"""
Dashboard Generator for REMAININGCONNECTIONS
Generates a static HTML dashboard from proxy / subscription / utility data files.

The page embeds a single CONFIG JSON (all prints stay ASCII-safe on Windows
cp1251 consoles) and renders five tabs in the browser:
  Subscriptions | TG Proxies | HTTP/SOCKS | Utilities | Speed Test
"""

import datetime
import json
import os
import sys


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


def _num(value, default=0):
    """Coerce value to a number (int/float); return default otherwise."""
    if isinstance(value, (int, float)):
        return value
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _truncate(value, limit):
    """Truncate a string to limit chars; pass non-strings through."""
    if isinstance(value, str):
        return value[:limit]
    return value


def _enrich_subscriptions(subscriptions):
    """
    Project subscription records to the fields the dashboard renders:
    name, repo, url, subscription_url, configs_count, status,
    updated_mins_ago, has_bs, content_sample (<= 200 chars), valid flag.
    Sorted: valid first, then by configs_count desc.
    """
    view = []
    for s in subscriptions:
        if not isinstance(s, dict):
            continue
        sub_url = s.get("subscription_url")
        sample = _truncate(s.get("content_sample"), 200)
        view.append({
            "name": s.get("name"),
            "repo": s.get("repo"),
            "url": s.get("url"),
            "subscription_url": sub_url,
            "configs_count": int(_num(s.get("configs_count"))),
            "status": s.get("status") or "unknown",
            "updated_mins_ago": s.get("updated_mins_ago"),
            "has_bs": bool(s.get("has_bs")),
            "content_sample": sample if isinstance(sample, str) else (sample or ""),
            "valid": bool(sub_url),
        })
    view.sort(key=lambda x: (0 if x["valid"] else 1, -x["configs_count"]))
    return view


def _enrich_utilities(utilities_payload):
    """
    Project utility records for the dashboard. Returns (list, summary).
    Keeps: id, name, full_name, url, description (<= 220), topics (<= 8),
    stars, forks, platforms_text, has_release, latest_release_tag,
    latest_release_url, latest_release_published_at, release_age_days,
    status, score. Sorted by score desc.
    """
    if not isinstance(utilities_payload, dict):
        utilities_payload = {}
    summary = utilities_payload.get("summary")
    if not isinstance(summary, dict):
        summary = {}
    view = []
    for u in utilities_payload.get("utilities", []):
        if not isinstance(u, dict):
            continue
        desc = _truncate(u.get("description"), 220)
        topics = u.get("topics") or []
        view.append({
            "id": u.get("id"),
            "name": u.get("name"),
            "full_name": u.get("full_name"),
            "url": u.get("url"),
            "description": desc if isinstance(desc, str) else (desc or ""),
            "topics": [str(t) for t in list(topics)[:8] if t],
            "stars": u.get("stars"),
            "forks": u.get("forks"),
            "platforms_text": u.get("platforms_text"),
            "has_release": bool(u.get("has_release")),
            "latest_release_tag": u.get("latest_release_tag"),
            "latest_release_url": u.get("latest_release_url"),
            "latest_release_published_at": u.get("latest_release_published_at"),
            "release_age_days": u.get("release_age_days"),
            "status": u.get("status"),
            "score": u.get("score"),
        })
    view.sort(key=lambda x: _num(x.get("score")), reverse=True)
    return view, summary


def _tg_card(p):
    """Project one TG proxy record to the fields rendered on a card."""
    return {
        "host": p.get("host") or p.get("server"),
        "port": p.get("port"),
        "protocol": p.get("protocol") or "unknown",
        "status": p.get("status") or "unknown",
        "latency_ms": p.get("latency_ms"),
        "tg_url": p.get("tg_url"),
        "tme_url": p.get("tme_url"),
    }


def _tg_sort_key(card):
    """Working first, then by latency asc (None/NaN treated as infinite)."""
    latency = _num(card.get("latency_ms"), None)
    latency_val = latency if latency is not None else float("inf")
    return (0 if card.get("status") == "working" else 1, latency_val)


# ---------------------------------------------------------------------------
# HTML template. Data is injected by replacing "__SAFE_JSON__" (NOT .format:
# the JS below is full of { } braces). Cards/ids match docs/configs.js:
#   - #subsGrid cards: .card with h3 + [data-copy] button  -> "Show configs"
#   - #proxiesList cards: .card with .font-mono "host:port" and a
#     <div class="flex items-center gap-2 mt-3"></div> row -> browser ping
# ---------------------------------------------------------------------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>REMAININGCONNECTIONS Dashboard</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        .card { background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; }
        .badge { display: inline-block; padding: 0.15rem 0.5rem; border-radius: 9999px; font-size: 0.75rem; font-weight: 600; line-height: 1.3; white-space: nowrap; }
        .badge-success { background: #065f46; color: #6ee7b7; }
        .badge-warning { background: #78350f; color: #fde68a; }
        .badge-danger { background: #7f1d1d; color: #fca5a5; }
        .badge-neutral { background: #1e3a5f; color: #93c5fd; }
        .badge-platform { background: #4c1d95; color: #c4b5fd; }
        .chip { display: inline-block; padding: 0.05rem 0.5rem; border-radius: 9999px; background: #0f172a; border: 1px solid #334155; font-size: 0.65rem; color: #94a3b8; }
        .btn { display: inline-flex; align-items: center; justify-content: center; padding: 0.5rem 1rem; border-radius: 0.375rem; font-size: 0.875rem; font-weight: 500; text-decoration: none; cursor: pointer; border: none; transition: opacity 0.2s; }
        .btn:hover { opacity: 0.85; }
        .btn:disabled { opacity: 0.45; cursor: not-allowed; }
        .btn-primary { background: #2563eb; color: #fff; }
        .btn-secondary { background: #374151; color: #d1d5db; }
        .btn-sm { padding: 0.25rem 0.6rem; font-size: 0.75rem; }
        .tab-btn { padding: 0.55rem 1rem; font-size: 0.875rem; font-weight: 600; color: #94a3b8; background: transparent; border: none; border-bottom: 2px solid transparent; cursor: pointer; }
        .tab-btn:hover { color: #e2e8f0; }
        .tab-btn.active { color: #60a5fa; border-bottom-color: #3b82f6; }
        .tab-panel { display: none; flex-direction: column; gap: 1rem; }
        .stat-chip { background: #1e293b; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.35rem 0.75rem; min-width: 88px; }
        .stat-chip .stat-label { font-size: 0.6rem; text-transform: uppercase; letter-spacing: 0.06em; color: #64748b; font-weight: 700; }
        .stat-chip .stat-value { font-size: 1.05rem; font-weight: 700; color: #e2e8f0; line-height: 1.25; }
        .empty-box { display: none; text-align: center; padding: 2.5rem 1rem; color: #94a3b8; border: 1px dashed #475569; border-radius: 0.5rem; font-size: 0.875rem; }
        .subs-card-muted { opacity: 0.6; }
        .ping-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
        .ping-good { background: #10b981; }
        .ping-ok { background: #f59e0b; }
        .ping-bad { background: #ef4444; }
        .text-muted { color: #94a3b8; }
        .text-faint { color: #64748b; }
        #sp-log { background: #0f172a; border: 1px solid #334155; border-radius: 0.5rem; padding: 0.75rem 1rem; font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.75rem; color: #94a3b8; height: 220px; overflow-y: auto; word-break: break-word; }
        .sp-bar { height: 12px; background: #0f172a; border: 1px solid #334155; border-radius: 9999px; overflow: hidden; }
        .sp-bar > div { height: 100%; width: 0%; background: linear-gradient(90deg, #2563eb, #22d3ee); transition: width 0.25s ease; }
    </style>
</head>
<body class="bg-slate-900 text-slate-100 min-h-screen">

    <!-- Sticky header: title + hero stats + tab nav -->
    <header class="sticky top-0 z-40 bg-slate-900/95 backdrop-blur border-b border-slate-700">
        <div class="container mx-auto px-4 max-w-7xl">
            <div class="py-3 flex flex-wrap items-center gap-x-6 gap-y-2">
                <div>
                    <h1 class="text-2xl font-bold leading-tight">REMAININGCONNECTIONS</h1>
                    <p class="text-xs text-slate-400">Proxy Discovery &amp; Monitoring Dashboard</p>
                </div>
                <div class="flex flex-wrap gap-2 ml-auto" id="hero-stats">
                    <div class="stat-chip"><div class="stat-label">Valid Subs</div><div class="stat-value" id="hero-valid-subs">0</div></div>
                    <div class="stat-chip"><div class="stat-label">Subs Found</div><div class="stat-value" id="hero-subs-found">0</div></div>
                    <div class="stat-chip"><div class="stat-label">TG Working</div><div class="stat-value text-green-400" id="hero-tg-working">0</div></div>
                    <div class="stat-chip"><div class="stat-label">HTTP+SOCKS Working</div><div class="stat-value text-blue-400" id="hero-hs-working">0</div></div>
                    <div class="stat-chip"><div class="stat-label">Utilities</div><div class="stat-value" id="hero-utils">0</div></div>
                </div>
            </div>
            <nav class="flex flex-wrap gap-1 -mb-px" id="tabs">
                <button class="tab-btn" data-tab="subs">Subscriptions</button>
                <button class="tab-btn" data-tab="tg">TG Proxies</button>
                <button class="tab-btn" data-tab="https">HTTP/SOCKS</button>
                <button class="tab-btn" data-tab="utils">Utilities</button>
                <button class="tab-btn" data-tab="speed">Speed Test</button>
            </nav>
        </div>
    </header>

    <main class="container mx-auto px-4 py-6 max-w-7xl">

        <!-- Toolbar: search filters the cards of the current tab -->
        <div class="card p-3 mb-4 flex flex-wrap items-center gap-3">
            <span class="text-sm font-semibold text-slate-300">Dashboard</span>
            <input type="text" id="search-input" placeholder="Search current tab (name, host, port, tag...)" autocomplete="off"
                   class="px-3 py-2 bg-slate-800 border border-slate-600 rounded text-sm focus:outline-none focus:border-blue-500 w-full sm:w-96">
            <span class="text-sm text-muted ml-auto" id="show-counter"></span>
        </div>

        <!-- ============ Tab: Subscriptions ============ -->
        <section id="panel-subs" class="tab-panel">
            <div class="flex flex-wrap items-center gap-2">
                <span class="text-sm text-muted">Filter:</span>
                <button id="subs-mode-valid" class="btn btn-primary btn-sm">Valid only</button>
                <button id="subs-mode-all" class="btn btn-secondary btn-sm">All</button>
                <span class="text-xs text-faint ml-auto">Subscriptions with a config URL can be copied and previewed (Show configs).</span>
            </div>
            <div id="subsGrid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"></div>
            <div id="subs-empty" class="empty-box" data-no-data="No subscriptions found in the data files."></div>
        </section>

        <!-- ============ Tab: TG Proxies ============ -->
        <section id="panel-tg" class="tab-panel">
            <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
                <div class="card p-3"><div class="text-xs text-muted uppercase tracking-wide font-bold">Total Checked</div><div class="text-2xl font-bold" id="tg-total">0</div></div>
                <div class="card p-3"><div class="text-xs text-muted uppercase tracking-wide font-bold">Working</div><div class="text-2xl font-bold text-green-400" id="tg-working">0</div></div>
                <div class="card p-3"><div class="text-xs text-muted uppercase tracking-wide font-bold">Timeout</div><div class="text-2xl font-bold text-yellow-400" id="tg-timeout">0</div></div>
                <div class="card p-3"><div class="text-xs text-muted uppercase tracking-wide font-bold">Failed</div><div class="text-2xl font-bold text-red-400" id="tg-failed">0</div></div>
            </div>
            <div id="proxiesList" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"></div>
            <div id="tg-empty" class="empty-box" data-no-data="No working TG proxies available yet."></div>
        </section>

        <!-- ============ Tab: HTTP/SOCKS ============ -->
        <section id="panel-https" class="tab-panel">
            <div id="httpSocksList" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"></div>
            <div id="https-empty" class="empty-box" data-no-data="No validated HTTP/SOCKS proxies yet — discovery workflow will fill this"></div>
        </section>

        <!-- ============ Tab: Utilities ============ -->
        <section id="panel-utils" class="tab-panel">
            <div id="utilsGrid" class="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4"></div>
            <div id="utils-empty" class="empty-box" data-no-data="No utilities found in the data files."></div>
        </section>

        <!-- ============ Tab: Speed Test ============ -->
        <section id="panel-speed" class="tab-panel">
            <div class="card p-6">
                <div class="flex flex-wrap items-center gap-3 mb-2">
                    <h2 class="text-xl font-semibold mr-auto">Speed Test</h2>
                    <button id="sp-start" class="btn btn-primary">Start</button>
                    <button id="sp-stop" class="btn btn-secondary" disabled>Stop</button>
                </div>
                <p class="text-sm text-muted mb-5">Measures your connection straight from the browser against Cloudflare speed endpoints. Runs entirely client-side — nothing is sent to this site's backend.</p>

                <div class="grid grid-cols-1 md:grid-cols-3 gap-4 mb-4">
                    <div class="border border-slate-700 rounded-lg p-4">
                        <div class="text-xs text-muted uppercase tracking-wide font-bold mb-1">Latency</div>
                        <div class="text-3xl font-bold" id="sp-latency">--</div>
                        <div class="text-xs text-faint mt-1">median of 5 requests</div>
                    </div>
                    <div class="border border-slate-700 rounded-lg p-4">
                        <div class="text-xs text-muted uppercase tracking-wide font-bold mb-1">Download</div>
                        <div class="text-3xl font-bold text-blue-400" id="sp-download">--</div>
                        <div class="sp-bar mt-2"><div id="sp-dl-bar"></div></div>
                        <div class="text-xs text-faint mt-1" id="sp-dl-info">25 MB test file</div>
                    </div>
                    <div class="border border-slate-700 rounded-lg p-4">
                        <div class="text-xs text-muted uppercase tracking-wide font-bold mb-1">Upload</div>
                        <div class="text-3xl font-bold text-emerald-400" id="sp-upload">--</div>
                        <div class="sp-bar mt-2"><div id="sp-ul-bar"></div></div>
                        <div class="text-xs text-faint mt-1" id="sp-ul-info">~16 MB payload</div>
                    </div>
                </div>

                <div class="text-sm mb-2 text-slate-300" id="sp-status">Idle — press Start to begin.</div>
                <div id="sp-log"></div>
            </div>
        </section>

    </main>

    <footer class="mt-10 border-t border-slate-800 py-6 text-center text-sm text-faint">
        <p>Generated by REMAININGCONNECTIONS | <a href="https://t.me/REMAININGCONNECTIONS" class="text-blue-400 hover:underline" target="_blank" rel="noopener">t.me/REMAININGCONNECTIONS</a></p>
    </footer>

    <script>
    const CONFIG = __SAFE_JSON__;

    // ---------- State ----------
    let currentTab = 'subs';
    let searchQuery = '';
    let subsValidOnly = true;

    // ---------- Helpers ----------
    function esc(v) {
        return String(v === null || v === undefined ? '' : v)
            .replaceAll('&', '&amp;')
            .replaceAll('<', '&lt;')
            .replaceAll('>', '&gt;')
            .replaceAll('"', '&quot;')
            .replaceAll("'", '&#039;');
    }

    function badge(text, kind) {
        return '<span class="badge badge-' + kind + '">' + esc(text) + '</span>';
    }

    function setText(id, text) {
        const el = document.getElementById(id);
        if (el) el.textContent = text;
    }

    function fmtLatency(ms) {
        const n = Number(ms);
        return Number.isFinite(n) ? n.toFixed(2) + ' ms' : '';
    }

    // ---------- Render: hero stats ----------
    function renderHero() {
        const subs = CONFIG.subscriptions || [];
        const tgStats = CONFIG.tg_stats || {};
        const utils = CONFIG.utilities || [];
        setText('hero-valid-subs', subs.filter((s) => s.valid).length.toLocaleString());
        setText('hero-subs-found', (CONFIG.subscriptions_count != null ? CONFIG.subscriptions_count : subs.length).toLocaleString());
        const tgWorking = tgStats.working != null ? tgStats.working : (CONFIG.tg_proxies || []).filter((p) => p.status === 'working').length;
        setText('hero-tg-working', tgWorking.toLocaleString());
        setText('hero-hs-working', (CONFIG.working_proxies || 0).toLocaleString());
        setText('hero-utils', (utils.length || (CONFIG.utilities_summary && CONFIG.utilities_summary.total_utilities) || 0).toLocaleString());
    }

    // ---------- Render: TG summary strip ----------
    function renderTgSummary() {
        const st = CONFIG.tg_stats || {};
        const by = st.by_status || {};
        let failed = 0;
        Object.entries(by).forEach(([k, v]) => { if (k !== 'working' && k !== 'timeout') failed += v; });
        setText('tg-total', (st.total != null ? st.total : 0).toLocaleString());
        setText('tg-working', ((by.working != null ? by.working : st.working) || 0).toLocaleString());
        setText('tg-timeout', (by.timeout || 0).toLocaleString());
        setText('tg-failed', failed.toLocaleString());
    }

    // ---------- Card builders ----------
    const SUB_BADGES = { active: 'success', unknown: 'neutral' };

    function subCard(s) {
        const title = s.name || s.repo || 'unknown subscription';
        const valid = s.valid === true;
        const statusKind = SUB_BADGES[s.status] || 'neutral';
        const repoHref = s.url || '#';
        const repoText = s.repo || s.url || '';
        const updated = (s.updated_mins_ago !== null && s.updated_mins_ago !== undefined)
            ? '<span class="text-xs text-faint">updated ' + esc(s.updated_mins_ago) + 'm ago</span>' : '';
        const actions = valid
            ? '<button class="btn btn-primary btn-sm" data-copy="' + esc(s.subscription_url) + '">Copy URL</button>'
            : '<a class="btn btn-secondary btn-sm" href="' + esc(repoHref) + '" target="_blank" rel="noopener">Open repo</a>';
        const sample = s.content_sample
            ? '<p class="text-xs text-slate-400 mt-2 leading-relaxed">' + esc(s.content_sample) + '</p>' : '';
        const search = [title, s.repo || '', s.url || '', s.status || ''].join(' ').toLowerCase();
        return '<div class="card p-4 flex flex-col ' + (valid ? '' : 'subs-card-muted') + '" data-valid="' + (valid ? '1' : '0') + '" data-search="' + esc(search) + '">'
            + '<div class="flex items-start justify-between gap-2 mb-2">'
            + '<h3 class="font-semibold text-sm break-all leading-snug">' + esc(title) + '</h3>'
            + '<div class="flex gap-1 flex-shrink-0 flex-wrap justify-end">' + badge(s.status || 'unknown', statusKind) + badge((s.configs_count || 0) + ' configs', 'platform') + '</div>'
            + '</div>'
            + '<div class="flex flex-wrap items-center gap-x-3 gap-y-1 mb-1">'
            + '<a class="text-blue-400 hover:underline text-xs break-all" href="' + esc(repoHref) + '" target="_blank" rel="noopener">' + esc(repoText || repoHref) + '</a>'
            + updated
            + '</div>'
            + sample
            + '<div class="flex items-center gap-2 pt-3 mt-auto">' + actions + '</div>'
            + '</div>';
    }

    function renderSubs() {
        const grid = document.getElementById('subsGrid');
        if (!grid) return;
        const subs = CONFIG.subscriptions || [];
        grid.innerHTML = subs.map(subCard).join('');
    }

    const PROXY_BADGES = { working: 'success', timeout: 'warning' };

    function proxyStatusBadge(status) {
        const kind = PROXY_BADGES[status] || 'danger';
        return badge(status || 'unknown', kind);
    }

    function tgCard(p) {
        const host = p.host || p.server || '';
        const hostPort = host + ':' + p.port;
        const proto = (p.protocol || 'unknown').toUpperCase();
        const lat = fmtLatency(p.latency_ms);
        const search = [host, p.port, p.protocol || '', p.status || ''].join(' ').toLowerCase();
        const buttons = [];
        if (p.tg_url) buttons.push('<a class="btn btn-primary btn-sm" href="' + esc(p.tg_url) + '">Connect in Telegram</a>');
        if (p.tme_url) buttons.push('<a class="btn btn-secondary btn-sm" href="' + esc(p.tme_url) + '" target="_blank" rel="noopener">t.me link</a>');
        return '<div class="card p-4 flex flex-col" data-search="' + esc(search) + '">'
            + '<div class="flex items-center justify-between gap-2 flex-wrap mb-1">'
            + '<span class="font-mono text-base font-semibold break-all">' + esc(hostPort) + '</span>'
            + badge(proto, 'platform')
            + '</div>'
            + '<div class="flex flex-wrap items-center gap-2">' + proxyStatusBadge(p.status)
            + (lat ? '<span class="text-xs text-slate-400">' + esc(lat) + '</span>' : '')
            + '</div>'
            + '<div class="flex items-center gap-2 mt-3"></div>'
            + (buttons.length ? '<div class="flex flex-wrap gap-2 mt-2">' + buttons.join('') + '</div>' : '')
            + '</div>';
    }

    function renderTg() {
        const list = document.getElementById('proxiesList');
        if (!list) return;
        const proxies = CONFIG.tg_proxies || [];
        list.innerHTML = proxies.map(tgCard).join('');
    }

    function hsCard(p) {
        const host = p.host || p.server || '';
        const hostPort = host + ':' + p.port;
        const proto = (p.protocol || p.type || 'unknown').toUpperCase();
        const lat = fmtLatency(p.latency_ms);
        const search = [host, p.port, p.protocol || p.type || '', p.status || '', p.country || ''].join(' ').toLowerCase();
        return '<div class="card p-4 flex flex-col" data-search="' + esc(search) + '">'
            + '<div class="flex items-center justify-between gap-2 flex-wrap mb-1">'
            + '<span class="font-mono text-base font-semibold break-all">' + esc(hostPort) + '</span>'
            + badge(proto, 'platform')
            + '</div>'
            + '<div class="flex flex-wrap items-center gap-2">' + proxyStatusBadge(p.status || (p.working ? 'working' : 'unknown'))
            + (lat ? '<span class="text-xs text-slate-400">' + esc(lat) + '</span>' : '')
            + '</div>'
            + '</div>';
    }

    function renderHttpSocks() {
        const list = document.getElementById('httpSocksList');
        if (!list) return;
        const proxies = CONFIG.proxies || [];
        list.innerHTML = proxies.map(hsCard).join('');
    }

    const UTIL_BADGES = { active: 'success', stale: 'warning', outdated: 'danger' };

    function utilCard(u) {
        const statusKind = UTIL_BADGES[u.status] || 'neutral';
        const name = u.name || u.full_name || 'utility';
        const url = u.url || '#';
        const stars = Number(u.stars || 0).toLocaleString();
        const forks = Number(u.forks || 0).toLocaleString();
        const platforms = String(u.platforms_text || '')
            .split(',')
            .map((t) => t.trim())
            .filter(Boolean)
            .slice(0, 6)
            .map((t) => badge(t, 'platform'))
            .join(' ');
        const release = u.has_release
            ? '<div class="text-xs text-slate-400 mt-2">Release: <a class="text-blue-400 hover:underline break-all" href="' + esc(u.latest_release_url || url) + '" target="_blank" rel="noopener">' + esc(u.latest_release_tag || 'release') + '</a>'
            + (u.release_age_days !== null && u.release_age_days !== undefined ? ' (' + esc(u.release_age_days) + 'd ago)' : '') + '</div>' : '';
        const topics = (u.topics || []).slice(0, 5).map((t) => '<span class="chip">' + esc(t) + '</span>').join(' ');
        const search = [name, u.full_name || '', u.url || '', u.description || '', u.status || ''].join(' ').toLowerCase();
        return '<div class="card p-4 flex flex-col" data-search="' + esc(search) + '">'
            + '<div class="flex items-start justify-between gap-2 mb-1">'
            + '<h3 class="font-semibold text-sm break-all leading-snug"><a class="text-blue-400 hover:underline" href="' + esc(url) + '" target="_blank" rel="noopener">' + esc(name) + '</a></h3>'
            + badge(u.status || 'unknown', statusKind)
            + '</div>'
            + (u.description ? '<p class="text-xs text-slate-400 leading-relaxed mb-2">' + esc(u.description) + '</p>' : '')
            + '<div class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs mb-2">'
            + '<span class="text-yellow-400 font-semibold">&#9733; ' + stars + '</span>'
            + '<span class="text-faint">' + forks + ' forks</span>'
            + (platforms ? '<span class="flex flex-wrap gap-1">' + platforms + '</span>' : '')
            + '</div>'
            + release
            + (topics ? '<div class="flex flex-wrap gap-1 mt-auto pt-2">' + topics + '</div>' : '')
            + '</div>';
    }

    function renderUtils() {
        const grid = document.getElementById('utilsGrid');
        if (!grid) return;
        const utils = CONFIG.utilities || [];
        grid.innerHTML = utils.map(utilCard).join('');
    }

    // ---------- Filters / search ----------
    const TAB_GRIDS = {
        subs: { grid: 'subsGrid', empty: 'subs-empty' },
        tg: { grid: 'proxiesList', empty: 'tg-empty' },
        https: { grid: 'httpSocksList', empty: 'https-empty' },
        utils: { grid: 'utilsGrid', empty: 'utils-empty' },
    };

    function applyFilters() {
        const conf = TAB_GRIDS[currentTab];
        const counter = document.getElementById('show-counter');
        if (!conf) {
            if (counter) counter.textContent = '';
            return;
        }
        const grid = document.getElementById(conf.grid);
        const empty = document.getElementById(conf.empty);
        if (!grid) return;
        const cards = Array.prototype.slice.call(grid.querySelectorAll('.card'));
        const q = searchQuery.trim().toLowerCase();
        let shown = 0;
        cards.forEach((card) => {
            let ok = true;
            if (q && !(card.dataset.search || '').includes(q)) ok = false;
            if (ok && currentTab === 'subs' && subsValidOnly && card.dataset.valid !== '1') ok = false;
            card.style.display = ok ? '' : 'none';
            if (ok) shown += 1;
        });
        if (empty) {
            if (shown === 0) {
                empty.style.display = 'block';
                empty.textContent = cards.length === 0
                    ? (empty.dataset.noData || 'Nothing to show here yet.')
                    : 'No items match your filter.';
            } else {
                empty.style.display = 'none';
            }
        }
        if (counter) counter.textContent = 'Showing ' + shown + ' of ' + cards.length;
    }

    // ---------- Tab switching ----------
    function switchTab(name) {
        currentTab = name;
        document.querySelectorAll('.tab-btn').forEach((b) => {
            b.classList.toggle('active', b.dataset.tab === name);
        });
        document.querySelectorAll('.tab-panel').forEach((p) => {
            p.style.display = (p.id === 'panel-' + name) ? 'flex' : 'none';
        });
        applyFilters();
    }

    function setSubsMode(validOnly) {
        subsValidOnly = validOnly;
        const vBtn = document.getElementById('subs-mode-valid');
        const aBtn = document.getElementById('subs-mode-all');
        if (vBtn) { vBtn.classList.toggle('btn-primary', validOnly); vBtn.classList.toggle('btn-secondary', !validOnly); }
        if (aBtn) { aBtn.classList.toggle('btn-primary', !validOnly); aBtn.classList.toggle('btn-secondary', validOnly); }
        applyFilters();
    }

    // ---------- Speed Test (client-side, Cloudflare endpoints) ----------
    const SP = { running: false, stopRequested: false, abortCtrl: null, xhr: null };

    function spSetStatus(text, isError) {
        const el = document.getElementById('sp-status');
        if (!el) return;
        el.textContent = text;
        el.className = 'text-sm mb-2 ' + (isError ? 'text-red-400' : 'text-slate-300');
    }

    function spLog(msg) {
        const el = document.getElementById('sp-log');
        if (!el) return;
        const line = document.createElement('div');
        line.textContent = '[' + new Date().toLocaleTimeString('en-GB', { hour12: false }) + '] ' + msg;
        el.appendChild(line);
        while (el.children.length > 12) el.removeChild(el.firstChild);
        el.scrollTop = el.scrollHeight;
    }

    function spSetBig(id, text) {
        setText(id, text);
    }

    function spSetBar(id, pct) {
        const el = document.getElementById(id);
        if (el) el.style.width = Math.max(0, Math.min(100, pct)) + '%';
    }

    function spSetRunning(running) {
        SP.running = running;
        const start = document.getElementById('sp-start');
        const stop = document.getElementById('sp-stop');
        if (start) start.disabled = running;
        if (stop) stop.disabled = !running;
    }

    async function spMeasureLatency(signal) {
        const samples = [];
        for (let i = 0; i < 5; i++) {
            if (SP.stopRequested) throw new Error('Aborted');
            const url = 'https://speed.cloudflare.com/__down?bytes=1&cb=' + Date.now() + '-' + i;
            const t0 = performance.now();
            let resp;
            try {
                resp = await fetch(url, { method: 'HEAD', cache: 'no-store', signal });
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
            } catch (e) {
                if (SP.stopRequested || signal.aborted) throw new Error('Aborted');
                // Some networks reject HEAD; fall back to a GET of a 1-byte file.
                resp = await fetch(url, { method: 'GET', cache: 'no-store', signal });
                if (!resp.ok) throw new Error('HTTP ' + resp.status);
            }
            await resp.arrayBuffer();
            const ms = performance.now() - t0;
            samples.push(ms);
            spLog('latency probe ' + (i + 1) + '/5: ' + Math.round(ms) + ' ms');
        }
        samples.sort((a, b) => a - b);
        return samples[2]; // median of 5
    }

    async function spMeasureDownload(signal) {
        const total = 25000000;
        const url = 'https://speed.cloudflare.com/__down?bytes=' + total + '&cb=' + Date.now();
        const resp = await fetch(url, { cache: 'no-store', signal });
        if (!resp.ok) throw new Error('Download endpoint returned HTTP ' + resp.status);
        const reader = resp.body && resp.body.getReader ? resp.body.getReader() : null;
        if (!reader) {
            const t0 = performance.now();
            const buf = await resp.arrayBuffer();
            const secs = Math.max((performance.now() - t0) / 1000, 0.001);
            return { mbps: (buf.byteLength * 8) / secs / 1e6, bytes: buf.byteLength, secs };
        }
        const t0 = performance.now();
        let bytes = 0;
        for (;;) {
            const chunk = await reader.read();
            if (chunk.done) break;
            if (chunk.value) bytes += chunk.value.byteLength;
            const secs = (performance.now() - t0) / 1000;
            if (secs > 0.05) {
                const mbps = (bytes * 8) / secs / 1e6;
                spSetBig('sp-download', mbps.toFixed(2) + ' Mbps');
                spSetBar('sp-dl-bar', (bytes / total) * 100);
                const info = document.getElementById('sp-dl-info');
                if (info) info.textContent = (bytes / 1048576).toFixed(1) + ' MB / ' + (total / 1048576).toFixed(0) + ' MB';
            }
        }
        const secs = Math.max((performance.now() - t0) / 1000, 0.001);
        return { mbps: (bytes * 8) / secs / 1e6, bytes: bytes, secs: secs };
    }

    function spBuildPayload(targetBytes) {
        const oneMB = new Uint8Array(1048576);
        for (let off = 0; off < oneMB.length; off += 65536) {
            crypto.getRandomValues(oneMB.subarray(off, Math.min(off + 65536, oneMB.length)));
        }
        const parts = [];
        let total = 0;
        while (total + oneMB.length <= targetBytes) { parts.push(oneMB); total += oneMB.length; }
        return new Blob(parts, { type: 'application/octet-stream' });
    }

    function spMeasureUpload() {
        return new Promise((resolve, reject) => {
            let payload;
            try {
                payload = spBuildPayload(16 * 1048576); // ~16 MB
            } catch (e) {
                reject(new Error('Could not build upload payload: ' + e.message));
                return;
            }
            const xhr = new XMLHttpRequest();
            SP.xhr = xhr;
            const t0 = performance.now();
            let lastT = t0;
            let lastLoaded = 0;

            xhr.upload.addEventListener('progress', (e) => {
                if (SP.stopRequested) { try { xhr.abort(); } catch (err) {} return; }
                const now = performance.now();
                const dt = (now - lastT) / 1000;
                if (e.lengthComputable && dt >= 0.2) {
                    const instantMbps = ((e.loaded - lastLoaded) * 8) / dt / 1e6;
                    spSetBig('sp-upload', instantMbps.toFixed(2) + ' Mbps');
                    spSetBar('sp-ul-bar', (e.loaded / e.total) * 100);
                    const info = document.getElementById('sp-ul-info');
                    if (info) info.textContent = (e.loaded / 1048576).toFixed(1) + ' MB / ' + (e.total / 1048576).toFixed(1) + ' MB';
                    spLog('upload ' + Math.round(e.loaded / 1048576) + ' / ' + Math.round(e.total / 1048576) + ' MB — ' + instantMbps.toFixed(2) + ' Mbps');
                    lastT = now;
                    lastLoaded = e.loaded;
                }
            });

            xhr.addEventListener('load', () => {
                const secs = Math.max((performance.now() - t0) / 1000, 0.001);
                if (xhr.status >= 200 && xhr.status < 300) {
                    resolve({ mbps: (payload.size * 8) / secs / 1e6, bytes: payload.size, secs: secs, status: xhr.status });
                } else {
                    reject(new Error('Upload endpoint returned HTTP ' + xhr.status));
                }
            });
            xhr.addEventListener('error', () => reject(new Error('Upload failed: network error (endpoint unreachable or blocked)')));
            xhr.addEventListener('timeout', () => reject(new Error('Upload timed out after 120 s')));
            xhr.addEventListener('abort', () => reject(new Error('Aborted')));
            try {
                xhr.open('POST', 'https://speed.cloudflare.com/__up?cb=' + Date.now());
                xhr.timeout = 120000;
                xhr.send(payload);
            } catch (e) {
                reject(new Error('Upload could not start: ' + e.message));
            }
        });
    }

    async function runSpeedTest() {
        if (SP.running) return;
        SP.stopRequested = false;
        SP.abortCtrl = new AbortController();
        const signal = SP.abortCtrl.signal;
        spSetRunning(true);
        spSetBig('sp-latency', '--');
        spSetBig('sp-download', '--');
        spSetBig('sp-upload', '--');
        spSetBar('sp-dl-bar', 0);
        spSetBar('sp-ul-bar', 0);
        spSetStatus('Speed test started.');
        spLog('--- Speed test started ---');
        try {
            if (SP.stopRequested) throw new Error('Aborted');
            spSetStatus('Measuring latency (5 sequential probes)...');
            const ms = await spMeasureLatency(signal);
            spSetBig('sp-latency', Math.round(ms) + ' ms');
            spLog('Median latency: ' + Math.round(ms) + ' ms');

            if (SP.stopRequested) throw new Error('Aborted');
            spSetStatus('Measuring download (25 MB from speed.cloudflare.com)...');
            const dl = await spMeasureDownload(signal);
            spSetBig('sp-download', dl.mbps.toFixed(2) + ' Mbps');
            spSetBar('sp-dl-bar', 100);
            spLog('Download: ' + dl.mbps.toFixed(2) + ' Mbps (' + (dl.bytes / 1048576).toFixed(1) + ' MB in ' + dl.secs.toFixed(2) + ' s)');

            if (SP.stopRequested) throw new Error('Aborted');
            spSetStatus('Measuring upload (~16 MB POST to speed.cloudflare.com)...');
            const ul = await spMeasureUpload();
            spSetBig('sp-upload', ul.mbps.toFixed(2) + ' Mbps');
            spSetBar('sp-ul-bar', 100);
            spLog('Upload: ' + ul.mbps.toFixed(2) + ' Mbps (' + (ul.bytes / 1048576).toFixed(1) + ' MB in ' + ul.secs.toFixed(2) + ' s, HTTP ' + ul.status + ')');

            spSetStatus('Done. Latency ' + Math.round(ms) + ' ms · down ' + dl.mbps.toFixed(2) + ' Mbps · up ' + ul.mbps.toFixed(2) + ' Mbps');
            spLog('Speed test finished.');
        } catch (e) {
            const msg = (e && e.message) ? e.message : String(e);
            if (SP.stopRequested) {
                spSetStatus('Stopped by user.');
                spLog('Speed test stopped.');
            } else {
                spSetStatus('Speed test failed: ' + msg + ' — check your network / firewall and try again.', true);
                spLog('ERROR: ' + msg);
            }
        }
        spSetRunning(false);
        SP.abortCtrl = null;
        SP.xhr = null;
    }

    function stopSpeedTest() {
        if (!SP.running) return;
        SP.stopRequested = true;
        if (SP.abortCtrl) { try { SP.abortCtrl.abort(); } catch (e) {} }
        if (SP.xhr) { try { SP.xhr.abort(); } catch (e) {} }
    }

    // ---------- Init ----------
    function init() {
        renderHero();
        renderTgSummary();
        renderSubs();
        renderTg();
        renderHttpSocks();
        renderUtils();

        document.querySelectorAll('.tab-btn').forEach((btn) => {
            btn.addEventListener('click', () => switchTab(btn.dataset.tab));
        });
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => { searchQuery = e.target.value; applyFilters(); });
        }
        const vBtn = document.getElementById('subs-mode-valid');
        const aBtn = document.getElementById('subs-mode-all');
        if (vBtn) vBtn.addEventListener('click', () => setSubsMode(true));
        if (aBtn) aBtn.addEventListener('click', () => setSubsMode(false));

        const startBtn = document.getElementById('sp-start');
        const stopBtn = document.getElementById('sp-stop');
        if (startBtn) startBtn.addEventListener('click', runSpeedTest);
        if (stopBtn) stopBtn.addEventListener('click', stopSpeedTest);

        setSubsMode(true);
        switchTab('subs');
    }

    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }
    </script>
    <script src="configs.js"></script>
</body>
</html>
"""


class DashboardGenerator:
    """Builds the static HTML dashboard from proxy data files."""

    def __init__(self, data_dir="data", output_dir="docs"):
        self.data_dir = data_dir
        self.output_dir = output_dir

    def _load_tg_view(self):
        """
        Resolve the TG proxy source for the dashboard.

        Preferred source: data/tg_proxies_found.json (proxies as-is).
        If that list is empty, fall back to checked/tg_proxies_checked.json
        (repo root = parent of data_dir) and keep only status == 'working'.

        Returns (cards, stats, source_label). Stats are full counters over
        every proxy in the chosen source file (all statuses).
        """
        found = load_json_safe(
            os.path.join(self.data_dir, 'tg_proxies_found.json'), {"proxies": []}
        )
        found_proxies = found.get("proxies", []) if isinstance(found, dict) else []
        if found_proxies:
            source = "data/tg_proxies_found.json"
            all_proxies = [p for p in found_proxies if isinstance(p, dict)]
            selected = all_proxies
        else:
            repo_root = os.path.dirname(os.path.normpath(self.data_dir)) or "."
            checked_path = os.path.join(repo_root, "checked", "tg_proxies_checked.json")
            checked = load_json_safe(checked_path, {"proxies": []})
            all_proxies = checked.get("proxies", []) if isinstance(checked, dict) else []
            all_proxies = [p for p in all_proxies if isinstance(p, dict)]
            source = "checked/tg_proxies_checked.json (fallback)"
            selected = [p for p in all_proxies if p.get("status") == "working"]

        by_status = {}
        for p in all_proxies:
            status = p.get("status") or "unknown"
            by_status[status] = by_status.get(status, 0) + 1

        cards = [_tg_card(p) for p in selected]
        cards.sort(key=_tg_sort_key)
        cards = cards[:1000]

        stats = {
            "total": len(all_proxies),
            "working": by_status.get("working", 0),
            "by_status": by_status,
        }
        return cards, stats, source

    def load_data(self):
        """Load all data files and combine them into a single payload."""
        tg_data = load_json_safe(os.path.join(self.data_dir, 'tg_proxies_found.json'), {"proxies": []})
        http_data = load_json_safe(os.path.join(self.data_dir, 'http_proxies_found.json'), {"proxies": []})
        socks_data = load_json_safe(os.path.join(self.data_dir, 'socks_proxies_found.json'), {"proxies": []})
        subs_data = load_json_safe(os.path.join(self.data_dir, 'subscriptions_found.json'), {"subscriptions": []})
        utils_data = load_json_safe(os.path.join(self.data_dir, 'utils_found.json'), {"utilities": [], "summary": {}})
        health_data = load_json_safe(os.path.join(self.data_dir, 'health_metrics.json'), {})

        # Combine all proxies from different sources
        all_proxies = []
        all_proxies.extend(tg_data.get('proxies', []))
        all_proxies.extend(http_data.get('proxies', []))
        all_proxies.extend(socks_data.get('proxies', []))

        return {
            "proxies": all_proxies,
            "subscriptions": subs_data.get('subscriptions', []),
            "utilities": utils_data,
            "health": health_data,
            "build_info": {
                "generated_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
                "total_proxies": len(all_proxies),
            },
        }

    def generate_html(self, config_data):
        """
        Render the HTML template with the embedded CONFIG JSON.

        config_data is the payload produced by load_data(): raw proxies and
        subscription/utility records plus build_info.
        """
        build_info = config_data.get("build_info") or {}
        proxies = [p for p in config_data.get("proxies", []) if isinstance(p, dict)]
        subscriptions = [s for s in config_data.get("subscriptions", []) if isinstance(s, dict)]
        utilities_payload = config_data.get("utilities")
        if not isinstance(utilities_payload, dict):
            utilities_payload = {}
        now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        # Support both old 'working' field and new 'status' field
        working_count = sum(
            1 for p in proxies
            if p.get('status') == 'working' or p.get('working') is True
        )

        subs_view = _enrich_subscriptions(subscriptions)
        utils_view, utils_summary = _enrich_utilities(utilities_payload)
        tg_cards, tg_stats, tg_source = self._load_tg_view()

        embed = {
            "generated_at": build_info.get("generated_at") or now,
            "total_proxies": len(proxies),
            "working_proxies": working_count,
            "proxies": proxies[:1000],
            "subscriptions": subs_view,
            "tg_proxies": tg_cards,
            "utilities": utils_view,
            "utilities_summary": utils_summary,
            "subscriptions_count": len(subscriptions),
            "tg_stats": tg_stats,
            "generated_files_info": {
                "subscriptions": {"file": "data/subscriptions_found.json", "items": len(subs_view)},
                "tg_proxies": {"file": tg_source, "items": len(tg_cards), "stats_total": tg_stats.get("total", 0)},
                "http_proxies": {"file": "data/http_proxies_found.json"},
                "socks_proxies": {"file": "data/socks_proxies_found.json"},
                "utilities": {"file": "data/utils_found.json", "items": len(utils_view)},
                "health_metrics": {"file": "data/health_metrics.json"},
                "note": "TG cards fall back to checked/tg_proxies_checked.json when data/tg_proxies_found.json is empty; HTTP/SOCKS cards come from data/http_proxies_found.json + data/socks_proxies_found.json",
            },
        }

        # Sanitize JSON for embedding in JS
        safe_json = json.dumps(embed, ensure_ascii=False)
        safe_json = safe_json.replace('</script>', '<\\/script>')

        return HTML_TEMPLATE.replace('__SAFE_JSON__', safe_json)

    def run(self):
        """Generate the dashboard HTML and write it to the output directory."""
        data = self.load_data()
        html = self.generate_html(data)
        os.makedirs(self.output_dir, exist_ok=True)
        output_path = os.path.join(self.output_dir, "index.html")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)
        return output_path


def generate_dashboard():
    """CLI wrapper: generate the static HTML dashboard. ASCII output only."""
    print("[*] Starting dashboard generation...")

    generator = DashboardGenerator()
    data = generator.load_data()
    working_count = sum(
        1 for p in data["proxies"]
        if isinstance(p, dict) and (p.get('status') == 'working' or p.get('working') is True)
    )
    utils_payload = data.get("utilities")
    utils_count = len(utils_payload.get("utilities", [])) if isinstance(utils_payload, dict) else 0
    print(f"[*] Total proxies: {len(data['proxies'])}")
    print(f"[*] Working proxies: {working_count}")
    print(f"[*] Subscriptions: {len(data['subscriptions'])}")
    print(f"[*] Utilities: {utils_count}")

    output_path = generator.run()
    print(f"[OK] Dashboard generated: {output_path}")
    print(f"[OK] Total: {len(data['proxies'])}, Working: {working_count}")


if __name__ == "__main__":
    try:
        generate_dashboard()
        sys.exit(0)
    except Exception as e:
        print(f"[!] Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
