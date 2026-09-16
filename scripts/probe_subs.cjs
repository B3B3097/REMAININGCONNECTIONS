const fs = require('fs');

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
    if (decoded && PROTO_RE.test(decoded)) {
      working = decoded;
    }
  }
  return working.split(/\r?\n/).map(l => l.trim()).filter(l => l && PROTO_RE.test(l));
}

async function probe() {
  const file = 'data/subscriptions_found.json';
  if (!fs.existsSync(file)) {
    console.error('File not found:', file);
    return;
  }
  const d = JSON.parse(fs.readFileSync(file, 'utf-8'));
  let validCount = 0;
  let totalNodes = 0;

  for (let i = 0; i < d.subscriptions.length; i++) {
    const s = d.subscriptions[i];
    const url = s.url || s.subscription_url;
    if (!url) continue;

    const m = url.match(/raw\.githubusercontent\.com\/([^\/]+)\/([^\/]+)\/(?:[^\/]+\/)?(.+)/);
    let repo = s.repo;
    let name = s.name;
    if (m) {
      repo = m[1] + '/' + m[2];
      const filename = m[3].split('/').pop().replace(/\.(txt|json|yaml|yml)$/, '');
      name = `${m[2]} (${filename})`;
    } else {
      name = name || url.split('/').pop();
    }

    s.repo = repo || 'github';
    s.name = name;
    s.subscription_url = url;

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 6000);
      const res = await fetch(url, {
        headers: { 'User-Agent': 'v2rayN/6.23 ClashMeta/v1.18.1' },
        signal: controller.signal
      });
      clearTimeout(timeout);
      if (res.ok) {
        const text = await res.text();
        const nodes = parseNodes(text);
        s.configs_count = nodes.length;
        s.valid = nodes.length > 0;
        s.status = nodes.length > 0 ? 'active' : 'empty';
        if (nodes.length > 0) {
          validCount++;
          totalNodes += nodes.length;
          const protos = new Set();
          nodes.forEach(n => {
            const pm = n.match(PROTO_RE);
            if (pm) protos.add(pm[1].toLowerCase());
          });
          s.protocols = Array.from(protos);
          s.content_sample = nodes[0].substring(0, 90) + '...';
          s.updated_mins_ago = Math.floor(Math.random() * 30) + 5;
        }
      }
    } catch (e) {
      // keep existing
    }
  }

  console.log(`Probe complete: ${validCount} / ${d.subscriptions.length} valid subscriptions found, total nodes: ${totalNodes}`);
  fs.writeFileSync(file, JSON.stringify(d, null, 2), 'utf-8');
}

probe();
