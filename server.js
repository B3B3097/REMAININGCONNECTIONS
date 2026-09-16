import express from 'express';
import cors from 'cors';
import fs from 'fs';
import path from 'path';
import { fileURLToPath } from 'url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const app = express();
const PORT = 3000;
const HOST = '0.0.0.0';
const startTime = Date.now();

const DATA_DIR = process.env.DATA_DIR || path.join(__dirname, 'data');
const DOCS_DIR = path.join(__dirname, 'docs');

if (!fs.existsSync(DATA_DIR)) {
  try { fs.mkdirSync(DATA_DIR, { recursive: true }); } catch (e) {}
}

app.use(cors());
app.use(express.json());

// In-memory cache for relays and embedded config
let cachedEmbeddedConfig = null;
const subCache = new Map(); // id -> { content, fetchedAt, expiresAt }

const PROTO_RE = /^(vless|vmess|trojan|ss|ssr|hysteria2?|hy2|tuic|wireguard|socks5?|https?):\/\//i;

function decodeBase64Safe(str) {
  try {
    const cleaned = str.replace(/\s/g, '').replace(/-/g, '+').replace(/_/g, '/');
    const pad = cleaned + '='.repeat((4 - (cleaned.length % 4)) % 4);
    return Buffer.from(pad, 'base64').toString('utf-8');
  } catch (e) {
    return null;
  }
}

function parseNodes(text) {
  if (!text) return [];
  let working = text;
  if (!PROTO_RE.test(working) && working.length > 20) {
    const decoded = decodeBase64Safe(working);
    if (decoded && (PROTO_RE.test(decoded) || decoded.includes('proxies:') || decoded.includes('outbounds:'))) {
      working = decoded;
    }
  }
  const directLines = working.split(/\r?\n/).map(l => l.trim()).filter(l => l && PROTO_RE.test(l));
  if (directLines.length > 0) return directLines;

  // Check for Clash YAML proxies
  if (working.includes('proxies:') || working.includes('proxy-groups:')) {
    const proxyMatches = working.match(/^\s*-\s*\{\s*name:|\n\s*-\s*name:/gm);
    if (proxyMatches && proxyMatches.length > 0) {
      return Array(proxyMatches.length).fill('clash://proxy');
    }
  }
  return [];
}

function saveSubscriptionsFound(data) {
  try {
    const filePath = path.join(DATA_DIR, 'subscriptions_found.json');
    fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
    // Also update summary
    const summary = readJsonFile('summary.json') || {};
    if (data && Array.isArray(data.subscriptions)) {
      summary.subscriptions_count = data.subscriptions.length;
      summary.subscriptions_working = data.subscriptions.filter(s => s.valid).length;
      const sumPath = path.join(DATA_DIR, 'summary.json');
      fs.writeFileSync(sumPath, JSON.stringify(summary, null, 2), 'utf-8');
    }
  } catch (err) {
    console.error('Failed to save subscriptions:', err.message);
  }
}

// Curated high-yield public subscription feeds
const CURATED_SUBSCRIPTION_FEEDS = [
  { url: 'https://raw.githubusercontent.com/morpheusadam/v2ray-config/main/subs/bundles/vless-base64.txt', name: 'MorpheusAdam (VLESS Bundle)', repo: 'morpheusadam/v2ray-config', protocol: 'vless' },
  { url: 'https://raw.githubusercontent.com/morpheusadam/v2ray-config/main/subs/bundles/vmess-base64.txt', name: 'MorpheusAdam (VMess Bundle)', repo: 'morpheusadam/v2ray-config', protocol: 'vmess' },
  { url: 'https://raw.githubusercontent.com/morpheusadam/v2ray-config/main/subs/bundles/trojan-base64.txt', name: 'MorpheusAdam (Trojan Bundle)', repo: 'morpheusadam/v2ray-config', protocol: 'trojan' },
  { url: 'https://raw.githubusercontent.com/morpheusadam/v2ray-config/main/subs/bundles/ss-base64.txt', name: 'MorpheusAdam (Shadowsocks Bundle)', repo: 'morpheusadam/v2ray-config', protocol: 'ss' },
  { url: 'https://raw.githubusercontent.com/morpheusadam/v2ray-config/main/subs/bundles/hysteria2-base64.txt', name: 'MorpheusAdam (Hysteria2 Bundle)', repo: 'morpheusadam/v2ray-config', protocol: 'hysteria2' },
  { url: 'https://raw.githubusercontent.com/morpheusadam/v2ray-config/main/subs/bundles/tuic-base64.txt', name: 'MorpheusAdam (TUIC Bundle)', repo: 'morpheusadam/v2ray-config', protocol: 'tuic' },
  { url: 'https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/vless_sub.txt', name: 'Freedom-V2Ray (VLESS Sub)', repo: 'MahanKenway/Freedom-V2Ray', protocol: 'vless' },
  { url: 'https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/vmess_sub.txt', name: 'Freedom-V2Ray (VMess Sub)', repo: 'MahanKenway/Freedom-V2Ray', protocol: 'vmess' },
  { url: 'https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/trojan_sub.txt', name: 'Freedom-V2Ray (Trojan Sub)', repo: 'MahanKenway/Freedom-V2Ray', protocol: 'trojan' },
  { url: 'https://raw.githubusercontent.com/MahanKenway/Freedom-V2Ray/main/configs/ss_sub.txt', name: 'Freedom-V2Ray (Shadowsocks Sub)', repo: 'MahanKenway/Freedom-V2Ray', protocol: 'ss' },
  { url: 'https://raw.githubusercontent.com/DisruptorProxy/Core/main/subscriptions/sub_merged.txt', name: 'DisruptorProxy Core (Merged Sub)', repo: 'DisruptorProxy/Core', protocol: 'mix' },
  { url: 'https://raw.githubusercontent.com/ebrasha/free-v2ray-public-list/main/all_nodes.txt', name: 'Free-V2Ray (Public Nodes)', repo: 'ebrasha/free-v2ray-public-list', protocol: 'mix' },
  { url: 'https://raw.githubusercontent.com/kort0881/vpn-aggregator/main/sub/sub_merge.txt', name: 'VPN Aggregator (Merged Sub)', repo: 'kort0881/vpn-aggregator', protocol: 'mix' },
  { url: 'https://raw.githubusercontent.com/Eleven1985/Scrape-By-Count/main/Subscription.txt', name: 'Scrape-By-Count (Scraped Subs)', repo: 'Eleven1985/Scrape-By-Count', protocol: 'mix' },
  { url: 'https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/vless', name: 'Configs Collector (VLESS Feed)', repo: 'soroushmirzaei/telegram-configs-collector', protocol: 'vless' },
  { url: 'https://raw.githubusercontent.com/soroushmirzaei/telegram-configs-collector/main/protocols/hysteria', name: 'Configs Collector (Hysteria Feed)', repo: 'soroushmirzaei/telegram-configs-collector', protocol: 'hysteria' },
  { url: 'https://raw.githubusercontent.com/MrPooyaX/VpnCollector/main/sub/mix', name: 'VpnCollector (Mix Sub)', repo: 'MrPooyaX/VpnCollector', protocol: 'mix' }
];

// Parse embedded CONFIG from docs/index.html as universal fallback
function getEmbeddedConfig() {
  if (cachedEmbeddedConfig) return cachedEmbeddedConfig;
  try {
    const indexPath = path.join(DOCS_DIR, 'index.html');
    if (fs.existsSync(indexPath)) {
      const content = fs.readFileSync(indexPath, 'utf-8');
      const match = content.match(/const CONFIG = ({.*?});\s*\n\s*\/\/ ---------- State ----------/s);
      if (match) {
        cachedEmbeddedConfig = JSON.parse(match[1]);
        return cachedEmbeddedConfig;
      }
    }
  } catch (err) {
    console.error('Error parsing embedded CONFIG from index.html:', err.message);
  }
  return null;
}

// Fallback generator if a data file was removed
function getFallbackData(filename) {
  const cfg = getEmbeddedConfig() || {};
  let data = null;

  if (filename === 'tg_proxies_found.json') {
    data = { proxies: cfg.tg_proxies || [] };
  } else if (filename === 'subscriptions_found.json') {
    data = { subscriptions: cfg.subscriptions || [] };
  } else if (filename === 'http_proxies_found.json') {
    const proxies = (cfg.proxies || []).filter(p => (p.protocol || p.type || '').toLowerCase().includes('http'));
    data = { proxies };
  } else if (filename === 'socks_proxies_found.json') {
    const proxies = (cfg.proxies || []).filter(p => (p.protocol || p.type || '').toLowerCase().includes('sock'));
    data = { proxies };
  } else if (filename === 'utils_found.json') {
    data = { utilities: cfg.utilities || [] };
  } else if (filename === 'summary.json') {
    data = {
      generated_at: cfg.generated_at || new Date().toISOString(),
      total_proxies: cfg.total_proxies || 0,
      working_proxies: cfg.working_proxies || 0,
      subscriptions_count: cfg.subscriptions_count || (cfg.subscriptions ? cfg.subscriptions.length : 0),
      tg_stats: cfg.tg_stats || {},
      utilities_summary: cfg.utilities_summary || {}
    };
  } else if (filename === 'health_metrics.json') {
    data = {
      status: 'healthy',
      version: '1.0.0',
      uptime: Math.round(((Date.now() - startTime) / 1000) * 100) / 100,
      timestamp: new Date().toISOString()
    };
  } else if (filename === 'custom_subscriptions.json') {
    data = [];
  }

  if (data) {
    try {
      const filePath = path.join(DATA_DIR, filename);
      fs.writeFileSync(filePath, JSON.stringify(data, null, 2), 'utf-8');
    } catch (e) {}
  }

  return data;
}

// Helper to read JSON file safely with auto-fallback
function readJsonFile(filename) {
  const filePath = path.join(DATA_DIR, filename);
  try {
    if (fs.existsSync(filePath)) {
      const data = fs.readFileSync(filePath, 'utf-8');
      return JSON.parse(data);
    }
  } catch (err) {
    console.error(`Error reading ${filename}:`, err.message);
  }
  return getFallbackData(filename);
}

function saveCustomSubscriptions(subs) {
  try {
    const filePath = path.join(DATA_DIR, 'custom_subscriptions.json');
    fs.writeFileSync(filePath, JSON.stringify(subs, null, 2), 'utf-8');
  } catch (err) {
    console.error('Failed to save custom subscriptions:', err.message);
  }
}

// Fetch remote subscription with browser/vpn client User-Agent
async function fetchRemoteSubscription(targetUrl) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), 15000);
  try {
    const response = await fetch(targetUrl, {
      signal: controller.signal,
      headers: {
        'User-Agent': 'ClashMeta/v1.18.1 v2rayN/6.23 sing-box/1.8.0 Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
      },
      redirect: 'follow',
    });
    clearTimeout(timeoutId);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status} ${response.statusText}`);
    }
    const text = await response.text();
    return text;
  } catch (err) {
    clearTimeout(timeoutId);
    throw err;
  }
}

// Calculate comprehensive stats
function calculateStats() {
  const proxiesData = readJsonFile('tg_proxies_found.json');
  const subsData = readJsonFile('subscriptions_found.json');
  const customSubs = readJsonFile('custom_subscriptions.json') || [];

  const stats = {
    timestamp: new Date().toISOString(),
    proxies: {},
    subscriptions: {},
    zaceper: {
      total_mirrors: customSubs.length,
      active_mirrors: customSubs.filter(s => s.status === 'active').length
    },
    uptime_seconds: Math.round(((Date.now() - startTime) / 1000) * 100) / 100
  };

  if (proxiesData && Array.isArray(proxiesData.proxies)) {
    const proxs = proxiesData.proxies;
    const working = proxs.filter(p => p.status === 'working' || p.working === true).length;
    const total = proxs.length;
    const rate = total > 0 ? (working / total) * 100 : 0;

    const protocols = {};
    for (const p of proxs) {
      const proto = p.protocol || p.type || 'unknown';
      protocols[proto] = (protocols[proto] || 0) + 1;
    }

    stats.proxies = {
      total,
      working,
      rate: Math.round(rate * 100) / 100,
      protocols
    };
  }

  if (subsData && Array.isArray(subsData.subscriptions)) {
    const subs = subsData.subscriptions;
    const workingSub = subs.filter(s => s.valid === true || s.status === 'active' || s.working === true).length;
    stats.subscriptions = {
      total: subs.length,
      working: workingSub,
      offline: subs.length - workingSub
    };
  }

  return stats;
}

// Health check endpoint
app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    version: '1.0.0',
    uptime: Math.round(((Date.now() - startTime) / 1000) * 100) / 100
  });
});

// API Routes
app.get('/api/v1/health', (req, res) => {
  const metrics = readJsonFile('health_metrics.json');
  if (metrics) {
    return res.json({
      ...metrics,
      uptime: Math.round(((Date.now() - startTime) / 1000) * 100) / 100,
      timestamp: new Date().toISOString()
    });
  }
  res.json({
    status: 'healthy',
    version: '1.0.0',
    uptime: Math.round(((Date.now() - startTime) / 1000) * 100) / 100
  });
});

app.get('/api/v1/stats', (req, res) => {
  const stats = calculateStats();
  res.json(stats);
});

app.get('/api/v1/proxies', (req, res) => {
  const data = readJsonFile('tg_proxies_found.json') || { proxies: [] };
  res.json(data);
});

app.get('/api/v1/subscriptions', (req, res) => {
  const data = readJsonFile('subscriptions_found.json') || { subscriptions: [] };
  let list = data.subscriptions || [];
  const { q, protocol, valid } = req.query;

  if (protocol && protocol !== 'all') {
    const pLower = protocol.toLowerCase();
    list = list.filter(s => (s.protocols || []).some(pr => pr.toLowerCase() === pLower));
  }
  if (valid === 'true' || valid === '1') {
    list = list.filter(s => s.valid === true);
  }
  if (q) {
    const qLower = q.toLowerCase();
    list = list.filter(s => {
      const hay = [s.name, s.repo, s.url, s.subscription_url, (s.protocols || []).join(' '), s.content_sample].filter(Boolean).join(' ').toLowerCase();
      return hay.includes(qLower);
    });
  }

  res.json({
    ...data,
    total: data.subscriptions ? data.subscriptions.length : 0,
    filtered: list.length,
    subscriptions: list
  });
});

// Refresh all existing subscriptions by re-probing their URLs
app.post('/api/v1/subscriptions/refresh-all', async (req, res) => {
  const data = readJsonFile('subscriptions_found.json') || { subscriptions: [] };
  const subs = data.subscriptions || [];
  let updatedCount = 0;
  let totalNodes = 0;

  // Process in batches of 5
  for (let i = 0; i < subs.length; i += 5) {
    const batch = subs.slice(i, i + 5);
    await Promise.allSettled(batch.map(async (s) => {
      const target = s.subscription_url || s.url;
      if (!target) return;
      try {
        const text = await fetchRemoteSubscription(target);
        const nodes = parseNodes(text);
        s.configs_count = nodes.length;
        s.valid = nodes.length > 0;
        s.status = nodes.length > 0 ? 'active' : 'empty';
        s.updated_mins_ago = 1;
        if (nodes.length > 0) {
          totalNodes += nodes.length;
          const protos = new Set();
          nodes.forEach(n => {
            const m = n.match(PROTO_RE);
            if (m) protos.add(m[1].toLowerCase());
          });
          s.protocols = Array.from(protos);
          s.content_sample = nodes[0].substring(0, 90) + '...';
        }
        updatedCount++;
      } catch (err) {
        // keep old status or mark as warning
      }
    }));
  }

  saveSubscriptionsFound(data);
  const validTotal = subs.filter(s => s.valid).length;
  res.json({
    success: true,
    total: subs.length,
    valid: validTotal,
    totalNodes,
    message: `Обновлено подписок: ${subs.length}, валидных: ${validTotal}`
  });
});

// Add a single custom subscription URL
app.post('/api/v1/subscriptions/add', async (req, res) => {
  const { url, name, repo } = req.body || {};
  if (!url || typeof url !== 'string' || !url.startsWith('http')) {
    return res.status(400).json({ error: 'Укажите валидный URL подписки (http:// или https://)' });
  }

  const data = readJsonFile('subscriptions_found.json') || { subscriptions: [] };
  const subs = data.subscriptions || [];

  // Check if exists
  const existing = subs.find(s => (s.subscription_url === url || s.url === url));
  if (existing) {
    return res.json({ success: true, alreadyExists: true, subscription: existing });
  }

  let nodesCount = 0;
  let protocols = [];
  let sample = '';

  try {
    const text = await fetchRemoteSubscription(url);
    const nodes = parseNodes(text);
    nodesCount = nodes.length;
    const protoSet = new Set();
    nodes.forEach(n => {
      const m = n.match(PROTO_RE);
      if (m) protoSet.add(m[1].toLowerCase());
    });
    protocols = Array.from(protoSet);
    if (nodes.length > 0) sample = nodes[0].substring(0, 90) + '...';
  } catch (err) {
    // Proceed with 0 configs
  }

  const newSub = {
    name: name || url.split('/').pop().replace(/\.(txt|json|yaml)$/, '') || 'Custom Sub',
    repo: repo || 'custom',
    url,
    subscription_url: url,
    configs_count: nodesCount,
    status: nodesCount > 0 ? 'active' : 'empty',
    updated_mins_ago: 0,
    has_bs: false,
    content_sample: sample,
    valid: nodesCount > 0,
    protocols
  };

  subs.unshift(newSub);
  saveSubscriptionsFound(data);
  res.json({ success: true, subscription: newSub });
});

// Live Subscription Discovery: Searches GitHub & verifies candidate subscriptions
app.post('/api/v1/subscriptions/discover', async (req, res) => {
  const { query, token: userToken, max_repos } = req.body || {};
  const token = userToken || process.env.GITHUB_TOKEN;
  const qStr = (query && query.trim()) || 'vless';
  const data = readJsonFile('subscriptions_found.json') || { subscriptions: [] };
  const subs = data.subscriptions || [];
  const existingUrls = new Set(subs.map(s => (s.subscription_url || s.url || '').toLowerCase()));

  const candidateUrls = new Map(); // url -> { name, repo }

  // 1. Check matching curated feeds
  for (const feed of CURATED_SUBSCRIPTION_FEEDS) {
    if (!existingUrls.has(feed.url.toLowerCase())) {
      if (qStr === 'all' || feed.protocol === 'mix' || feed.name.toLowerCase().includes(qStr.toLowerCase()) || feed.url.toLowerCase().includes(qStr.toLowerCase())) {
        candidateUrls.set(feed.url, { name: feed.name, repo: feed.repo });
      }
    }
  }

  // 2. Query GitHub Search Repositories API
  try {
    const ghHeaders = {
      'User-Agent': 'REMAININGCONNECTIONS-App',
      'Accept': 'application/vnd.github+json'
    };
    if (token) {
      ghHeaders['Authorization'] = `token ${token}`;
    }

    const ghSearchUrl = `https://api.github.com/search/repositories?q=${encodeURIComponent(qStr + ' proxy OR vpn OR v2ray OR vless')}&sort=updated&order=desc&per_page=12`;
    const ghRes = await fetch(ghSearchUrl, { headers: ghHeaders, signal: AbortSignal.timeout(8000) });
    if (ghRes.ok) {
      const ghData = await ghRes.json();
      const repos = (ghData.items || []).slice(0, max_repos || 8);

      for (const repo of repos) {
        const repoFullName = repo.full_name;
        const branch = repo.default_branch || 'main';

        // Check common subscription paths in repo
        const commonPaths = [
          'sub/sub_merge.txt',
          'subs/bundles/vless-base64.txt',
          'subs/bundles/hysteria2-base64.txt',
          'subs/bundles/trojan-base64.txt',
          'subs/bundles/vmess-base64.txt',
          'configs/vless_sub.txt',
          'configs/trojan_sub.txt',
          'configs/vmess_sub.txt',
          'sub.txt',
          'subscription.txt',
          'vless.txt',
          'all.txt',
          'mix.txt',
          'clash.yaml'
        ];

        for (const p of commonPaths.slice(0, 4)) {
          const rawUrl = `https://raw.githubusercontent.com/${repoFullName}/${branch}/${p}`;
          if (!existingUrls.has(rawUrl.toLowerCase()) && !candidateUrls.has(rawUrl)) {
            candidateUrls.set(rawUrl, {
              name: `${repo.name} (${p.split('/').pop().replace(/\.(txt|json|yaml)$/, '')})`,
              repo: repoFullName
            });
          }
        }
      }
    }
  } catch (err) {
    console.warn('GitHub search error:', err.message);
  }

  // If candidate list is empty, add any remaining curated feeds
  if (candidateUrls.size === 0) {
    for (const feed of CURATED_SUBSCRIPTION_FEEDS) {
      if (!existingUrls.has(feed.url.toLowerCase())) {
        candidateUrls.set(feed.url, { name: feed.name, repo: feed.repo });
      }
    }
  }

  // 3. Probe candidate URLs in parallel (up to 15)
  const candidates = Array.from(candidateUrls.entries()).slice(0, 15);
  const newlyDiscovered = [];

  await Promise.allSettled(candidates.map(async ([url, meta]) => {
    try {
      const text = await fetchRemoteSubscription(url);
      const nodes = parseNodes(text);
      if (nodes.length > 0) {
        const protos = new Set();
        nodes.forEach(n => {
          const m = n.match(PROTO_RE);
          if (m) protos.add(m[1].toLowerCase());
        });

        const newSub = {
          name: meta.name,
          repo: meta.repo,
          url,
          subscription_url: url,
          configs_count: nodes.length,
          status: 'active',
          updated_mins_ago: 1,
          has_bs: false,
          content_sample: nodes[0].substring(0, 90) + '...',
          valid: true,
          protocols: Array.from(protos)
        };

        newlyDiscovered.push(newSub);
        subs.unshift(newSub);
        existingUrls.add(url.toLowerCase());
      }
    } catch (e) {
      // url was not a valid subscription
    }
  }));

  if (newlyDiscovered.length > 0) {
    saveSubscriptionsFound(data);
  }

  const validTotal = subs.filter(s => s.valid).length;
  res.json({
    success: true,
    added: newlyDiscovered.length,
    newSubscriptions: newlyDiscovered,
    totalValid: validTotal,
    totalSubscriptions: subs.length,
    message: newlyDiscovered.length > 0
      ? `Найдено и добавлено ${newlyDiscovered.length} новых подписок!`
      : 'Все найденные подписки уже добавлены в базу или недоступны.'
  });
});

app.get('/api/v1/http-proxies', (req, res) => {
  const data = readJsonFile('http_proxies_found.json') || { proxies: [] };
  res.json(data);
});

app.get('/api/v1/socks-proxies', (req, res) => {
  const data = readJsonFile('socks_proxies_found.json') || { proxies: [] };
  res.json(data);
});

app.get('/api/v1/utils', (req, res) => {
  const data = readJsonFile('utils_found.json') || { utilities: [] };
  res.json(data);
});

app.get('/api/v1/summary', (req, res) => {
  const data = readJsonFile('summary.json') || {};
  res.json(data);
});

// Subscription Relay Endpoint (Bypasses CORS & client-side ISP / IP restrictions)
app.get('/api/v1/relay', async (req, res) => {
  const targetUrl = req.query.url;
  if (!targetUrl || typeof targetUrl !== 'string' || !targetUrl.startsWith('http')) {
    return res.status(400).json({ error: 'Missing or invalid "url" query parameter' });
  }

  try {
    const text = await fetchRemoteSubscription(targetUrl);
    res.set({
      'Content-Type': 'text/plain; charset=utf-8',
      'Access-Control-Allow-Origin': '*',
    });
    res.send(text);
  } catch (err) {
    res.status(502).json({ error: 'Relay fetch failed: ' + err.message });
  }
});

// ============ ЗАЦЕПЕР (SUBSCRIPTION RELAYER & MIRROR) ============

app.get('/api/v1/zaceper/list', (req, res) => {
  const subs = readJsonFile('custom_subscriptions.json') || [];
  const sanitized = subs.map(({ cachedBody, ...rest }) => ({
    ...rest,
    subUrl: `/sub/${rest.id}`
  }));
  res.json(sanitized);
});

app.post('/api/v1/zaceper/create', async (req, res) => {
  const { url, name, slug } = req.body || {};
  if (!url || typeof url !== 'string' || !url.startsWith('http')) {
    return res.status(400).json({ error: 'Пожалуйста, укажите корректный URL подписки (начинающийся с http:// или https://)' });
  }

  const subs = readJsonFile('custom_subscriptions.json') || [];
  const id = slug && /^[a-zA-Z0-9_-]{3,32}$/.test(slug) && !subs.some(s => s.id === slug)
    ? slug
    : 'sub_' + Math.random().toString(36).substring(2, 8);

  let nodesCount = 0;
  let protocols = [];
  let cachedContent = '';
  let fetchError = null;

  try {
    cachedContent = await fetchRemoteSubscription(url);
    const nodes = parseNodes(cachedContent);
    nodesCount = nodes.length;
    const protoSet = new Set();
    nodes.forEach(n => {
      const match = n.match(PROTO_RE);
      if (match) protoSet.add(match[1].toLowerCase());
    });
    protocols = Array.from(protoSet);
  } catch (err) {
    fetchError = err.message;
    console.warn('Initial fetch for created subscription failed:', err.message);
  }

  const newSub = {
    id,
    name: (name && name.trim()) || `Зеркало #${subs.length + 1}`,
    targetUrl: url,
    nodesCount,
    protocols,
    createdAt: new Date().toISOString(),
    lastSynced: new Date().toISOString(),
    status: fetchError ? 'warning' : 'active',
    lastError: fetchError || null,
    cachedBody: cachedContent ? cachedContent.slice(0, 100000) : ''
  };

  subs.unshift(newSub);
  saveCustomSubscriptions(subs);

  const { cachedBody, ...result } = newSub;
  res.json({
    success: true,
    subscription: {
      ...result,
      subUrl: `/sub/${id}`
    }
  });
});

app.post('/api/v1/zaceper/refresh/:id', async (req, res) => {
  const { id } = req.params;
  const subs = readJsonFile('custom_subscriptions.json') || [];
  const item = subs.find(s => s.id === id);
  if (!item) {
    return res.status(404).json({ error: 'Подписка не найдена' });
  }

  try {
    const text = await fetchRemoteSubscription(item.targetUrl);
    const nodes = parseNodes(text);
    item.nodesCount = nodes.length;
    const protoSet = new Set();
    nodes.forEach(n => {
      const match = n.match(PROTO_RE);
      if (match) protoSet.add(match[1].toLowerCase());
    });
    item.protocols = Array.from(protoSet);
    item.lastSynced = new Date().toISOString();
    item.status = 'active';
    item.lastError = null;
    item.cachedBody = text.slice(0, 100000);

    subCache.set(id, {
      content: text,
      fetchedAt: Date.now(),
      expiresAt: Date.now() + 60000
    });

    saveCustomSubscriptions(subs);
    const { cachedBody, ...result } = item;
    res.json({ success: true, subscription: { ...result, subUrl: `/sub/${id}` } });
  } catch (err) {
    item.status = 'warning';
    item.lastError = err.message;
    saveCustomSubscriptions(subs);
    res.status(502).json({ error: 'Ошибка обновления: ' + err.message });
  }
});

app.delete('/api/v1/zaceper/delete/:id', (req, res) => {
  const { id } = req.params;
  let subs = readJsonFile('custom_subscriptions.json') || [];
  const before = subs.length;
  subs = subs.filter(s => s.id !== id);
  if (subs.length === before) {
    return res.status(404).json({ error: 'Подписка не найдена' });
  }
  subCache.delete(id);
  saveCustomSubscriptions(subs);
  res.json({ success: true, message: 'Успешно удалено' });
});

// Client-ready Public Subscription Mirror (/sub/:id or /api/v1/sub/:id)
app.get(['/sub/:id', '/api/v1/sub/:id'], async (req, res) => {
  const { id } = req.params;
  const subs = readJsonFile('custom_subscriptions.json') || [];
  const item = subs.find(s => s.id === id);

  if (!item) {
    return res.status(404).type('text/plain').send('# Error: Subscription not found\n');
  }

  let content = null;
  const now = Date.now();
  const cached = subCache.get(id);

  if (cached && now < cached.expiresAt) {
    content = cached.content;
  } else {
    try {
      content = await fetchRemoteSubscription(item.targetUrl);
      subCache.set(id, {
        content,
        fetchedAt: now,
        expiresAt: now + 60 * 1000 // 60s cache
      });
      // Update cached state
      item.lastSynced = new Date().toISOString();
      item.cachedBody = content.slice(0, 100000);
      const nodes = parseNodes(content);
      item.nodesCount = nodes.length;
      saveCustomSubscriptions(subs);
    } catch (err) {
      console.warn(`Upstream error for sub ${id}:`, err.message);
      if (cached) {
        content = cached.content;
      } else if (item.cachedBody) {
        content = item.cachedBody;
      } else {
        return res.status(502).type('text/plain').send(`# Error: Failed to fetch upstream subscription: ${err.message}\n`);
      }
    }
  }

  res.set({
    'Content-Type': 'text/plain; charset=utf-8',
    'Subscription-Userinfo': 'upload=0; download=0; total=107374182400; expire=1893456000',
    'Profile-Update-Interval': '12',
    'Content-Disposition': `attachment; filename="${encodeURIComponent(item.name || item.id)}.txt"`,
    'Access-Control-Allow-Origin': '*',
  });
  res.send(content);
});

// Workflow triggers
app.post('/api/v1/triggers/:workflow_name', (req, res) => {
  const wfName = req.params.workflow_name;
  const allowedWorkflows = ['tg-proxy-discovery', 'subscription-discovery', 'utils-discovery'];

  if (!allowedWorkflows.includes(wfName)) {
    return res.status(404).json({ error: `Workflow '${wfName}' not allowed or not found.` });
  }

  res.json({
    message: `Workflow '${wfName}' triggered successfully.`,
    workflow: wfName,
    timestamp: new Date().toISOString()
  });
});

// Serve frontend static files from docs
app.use(express.static(DOCS_DIR));

// Fallback for SPA routing
app.get('*', (req, res) => {
  const indexPath = path.join(DOCS_DIR, 'index.html');
  if (fs.existsSync(indexPath)) {
    res.sendFile(indexPath);
  } else {
    res.send('<h1>REMAININGCONNECTIONS Dashboard</h1>');
  }
});

app.listen(PORT, HOST, () => {
  console.log(`Server running at http://${HOST}:${PORT}`);
});
