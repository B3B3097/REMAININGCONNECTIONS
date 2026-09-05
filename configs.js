/*
 * configs.js — self-contained module for REMAININGCONNECTIONS dashboard.
 * Adds: "Show configs" button on subscription cards, configs modal with
 * QR codes + copy + client deep-links, and browser-side ping for proxies.
 * No external dependencies; injects its own CSS and modal HTML.
 */
(() => {
  "use strict";

  // ---------- Constants ----------
  const PROTO_RE = /^(vless|vmess|trojan|ss|ssr|hysteria2?|hy2|tuic|wireguard|socks5?|https?):\/\//i;
  const QR_API = "https://api.qrserver.com/v1/create-qr-code/?size=180x180&data=";

  // CORS proxies as fallback when direct fetch fails
  const CORS_PROXIES = [
    (u) => `https://corsproxy.io/?url=${encodeURIComponent(u)}`,
    (u) => `https://api.allorigins.win/raw?url=${encodeURIComponent(u)}`,
    (u) => `https://cors-anywhere.herokuapp.com/${u}`,
  ];

  const CLIENT_LINKS = {
    clash: (sub, name) => `clash://install-config?url=${encodeURIComponent(sub)}&name=${encodeURIComponent(name || "sub")}`,
    clashmeta: (sub, name) => `clash://install-sub?url=${encodeURIComponent(sub)}&name=${encodeURIComponent(name || "sub")}`,
    hiddify: (sub) => `hiddify://subscription?url=${encodeURIComponent(sub)}`,
    singbox: (sub) => `sing-box://import-remote-profile?url=${encodeURIComponent(sub)}`,
    v2rayng: (sub) => `v2rayng://install-sub?url=${encodeURIComponent(sub)}`,
    v2rayn: (sub) => `v2rayn://install-sub?url=${encodeURIComponent(sub)}`,
    nekobox: (sub) => `nekobox://subscription?url=${encodeURIComponent(sub)}`,
    shadowrocket: (sub) => `shadowrocket://add/sub?url=${encodeURIComponent(sub)}`,
  };

  // ---------- Utils ----------
  const esc = (v) => {
    if (v === null || v === undefined) return "";
    return String(v)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;")
      .replaceAll("'", "&#039;");
  };

  const toast = (msg, type = "info") => {
    const c = document.getElementById("toastContainer");
    if (!c) return;
    const colors = {
      success: "border-l-4 border-emerald-400",
      error: "border-l-4 border-red-400",
      info: "border-l-4 border-blue-400",
    };
    const t = document.createElement("div");
    t.className = `toast ${colors[type] || colors.info}`;
    t.innerHTML = `<div class="text-sm">${esc(msg)}</div>`;
    c.appendChild(t);
    setTimeout(() => {
      t.style.opacity = "0";
      t.style.transform = "translateY(8px)";
      setTimeout(() => t.remove(), 250);
    }, 3000);
  };

  const copyText = async (text, msg) => {
    try {
      await navigator.clipboard.writeText(text);
      toast(msg || "Copied", "success");
    } catch (e) {
      // fallback
      const ta = document.createElement("textarea");
      ta.value = text;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      try { document.execCommand("copy"); toast(msg || "Copied", "success"); } catch (e2) { toast("Copy failed", "error"); }
      document.body.removeChild(ta);
    }
  };

  const decodeBase64 = (s) => {
    try {
      const cleaned = s.replace(/\s/g, "").replace(/-/g, "+").replace(/_/g, "/");
      const pad = cleaned + "=".repeat((4 - (cleaned.length % 4)) % 4);
      const bin = atob(pad);
      const bytes = new Uint8Array(bin.length);
      for (let i = 0; i < bin.length; i++) bytes[i] = bin.charCodeAt(i);
      return new TextDecoder("utf-8").decode(bytes);
    } catch (e) {
      return null;
    }
  };

  const parseNameFromConfig = (line) => {
    const m = line.match(/#([^#]*)$/);
    if (m) {
      try { return decodeURIComponent(m[1]).trim(); } catch (e) { return m[1].trim(); }
    }
    if (line.startsWith("vmess://")) {
      const payload = line.slice("vmess://".length);
      const json = decodeBase64(payload);
      if (json) {
        try {
          const obj = JSON.parse(json);
          if (obj && obj.ps) return obj.ps;
          if (obj && obj.add) return `${obj.add}:${obj.port || ""}`;
        } catch (e) {}
      }
    }
    return null;
  };

  const parseSubscription = (text) => {
    if (!text) return [];
    let working = text;
    const hasProto = PROTO_RE.test(working);
    if (!hasProto && working.length > 20) {
      const decoded = decodeBase64(working);
      if (decoded && PROTO_RE.test(decoded)) {
        working = decoded;
      }
    }
    const lines = working
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter((l) => l && PROTO_RE.test(l));
    return lines.map((line, i) => {
      const proto = (line.match(PROTO_RE) || [])[1] || "unknown";
      const name = parseNameFromConfig(line) || `${proto} #${i + 1}`;
      return { proto: proto.toLowerCase(), raw: line, name };
    });
  };

  const fetchSubscription = async (url) => {
    // Try direct fetch first
    try {
      const res = await fetch(url, { cache: "no-store" });
      if (res.ok) {
        const text = await res.text();
        if (text && text.length > 0) return text;
      }
    } catch (e) {
      // fall through to proxies
    }
    // Try CORS proxies
    for (const proxyFn of CORS_PROXIES) {
      try {
        const res = await fetch(proxyFn(url), { cache: "no-store" });
        if (res.ok) {
          const text = await res.text();
          if (text && text.length > 0) return text;
        }
      } catch (e) {
        // try next proxy
      }
    }
    throw new Error("All fetch attempts failed (CORS or network)");
  };

  // ---------- CSS ----------
  const css = `
  .rc-modal-overlay { position: fixed; inset: 0; z-index: 1000; background: rgba(0,0,0,0.72); backdrop-filter: blur(8px); -webkit-backdrop-filter: blur(8px); display: flex; align-items: center; justify-content: center; padding: 16px; animation: rcFade .18s ease; }
  @keyframes rcFade { from { opacity: 0; } to { opacity: 1; } }
  .rc-modal-box { background: rgba(17,24,39,0.96); border: 1px solid rgba(255,255,255,0.1); border-radius: 20px; max-width: 780px; width: 100%; max-height: 86vh; overflow: hidden; display: flex; flex-direction: column; box-shadow: 0 30px 70px rgba(0,0,0,0.5); }
  .rc-modal-header { padding: 16px 20px; border-bottom: 1px solid rgba(255,255,255,0.08); display: flex; justify-content: space-between; align-items: center; gap: 12px; }
  .rc-modal-body { padding: 14px 18px; overflow-y: auto; flex: 1; }
  .rc-config-item { background: rgba(255,255,255,0.03); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 12px; margin-bottom: 10px; display: flex; gap: 12px; align-items: flex-start; }
  .rc-config-qr { width: 72px; height: 72px; border-radius: 10px; background: #fff; flex-shrink: 0; overflow: hidden; }
  .rc-config-qr img { width: 100%; height: 100%; display: block; }
  .rc-config-info { flex: 1; min-width: 0; }
  .rc-config-name { font-weight: 700; font-size: 13px; word-break: break-all; }
  .rc-config-raw { font-family: "JetBrains Mono", monospace; font-size: 10px; color: #9ca3af; margin-top: 4px; word-break: break-all; max-height: 38px; overflow: hidden; }
  .rc-config-actions { display: flex; flex-wrap: wrap; gap: 6px; margin-top: 8px; }
  .rc-btn { display: inline-flex; align-items: center; justify-content: center; gap: 6px; border-radius: 10px; padding: 6px 10px; font-weight: 700; font-size: 11px; border: 1px solid transparent; cursor: pointer; transition: all .15s ease; text-decoration: none; }
  .rc-btn-primary { background: #3b82f6; color: #fff; }
  .rc-btn-primary:hover { background: #2563eb; }
  .rc-btn-secondary { background: rgba(255,255,255,0.05); border-color: rgba(255,255,255,0.1); color: #f9fafb; }
  .rc-btn-secondary:hover { background: rgba(255,255,255,0.1); }
  .rc-client-row { display: flex; flex-wrap: wrap; gap: 8px; padding: 12px 0; border-bottom: 1px solid rgba(255,255,255,0.06); margin-bottom: 12px; align-items: center; }
  .rc-client-label { font-size: 11px; color: #6b7280; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }
  .rc-ping-dot { width: 8px; height: 8px; border-radius: 999px; display: inline-block; }
  .rc-ping-good { background: #34d399; box-shadow: 0 0 8px rgba(52,211,153,0.6); }
  .rc-ping-medium { background: #fbbf24; box-shadow: 0 0 8px rgba(251,191,36,0.6); }
  .rc-ping-bad { background: #f87171; box-shadow: 0 0 8px rgba(248,113,113,0.6); }
  .rc-ping-loading { background: #6b7280; animation: rcPulse 1s ease-in-out infinite; }
  @keyframes rcPulse { 0%,100% { opacity: 0.4; } 50% { opacity: 1; } }
  .rc-configs-btn { width: 100%; margin-top: 8px; }
  .rc-loading { text-align: center; padding: 40px; color: #6b7280; }
  .rc-loading-spinner { display: inline-block; width: 32px; height: 32px; border: 3px solid rgba(255,255,255,0.1); border-top-color: #3b82f6; border-radius: 50%; animation: rcSpin .8s linear infinite; }
  @keyframes rcSpin { to { transform: rotate(360deg); } }
  `;
  const styleEl = document.createElement("style");
  styleEl.textContent = css;
  document.head.appendChild(styleEl);

  // ---------- Modal ----------
  const modalHtml = `
  <div id="rcConfigsModal" class="rc-modal-overlay" style="display:none;">
    <div class="rc-modal-box">
      <div class="rc-modal-header">
        <div>
          <div id="rcModalTitle" style="font-weight:900;font-size:16px;">Configs</div>
          <div id="rcModalSub" style="font-size:11px;color:#6b7280;margin-top:2px;word-break:break-all;"></div>
        </div>
        <button id="rcModalClose" class="rc-btn rc-btn-secondary">Close</button>
      </div>
      <div class="rc-modal-body" id="rcModalBody"></div>
    </div>
  </div>`;
  const modalHolder = document.createElement("div");
  modalHolder.innerHTML = modalHtml;
  document.body.appendChild(modalHolder.firstElementChild);

  const modal = document.getElementById("rcConfigsModal");
  const modalBody = document.getElementById("rcModalBody");
  const modalTitle = document.getElementById("rcModalTitle");
  const modalSub = document.getElementById("rcModalSub");

  const closeModal = () => {
    modal.style.display = "none";
    modalBody.innerHTML = "";
  };
  document.getElementById("rcModalClose").addEventListener("click", closeModal);
  modal.addEventListener("click", (e) => {
    if (e.target === modal) closeModal();
  });
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape" && modal.style.display !== "none") closeModal();
  });

  const openModal = (title, sub) => {
    modalTitle.textContent = title;
    modalSub.textContent = sub || "";
    modal.style.display = "flex";
    modalBody.innerHTML = `<div class="rc-loading"><div class="rc-loading-spinner"></div><div style="margin-top:12px;">Loading configs...</div></div>`;
  };

  const renderConfigs = (configs, subUrl, subName) => {
    if (!configs.length) {
      modalBody.innerHTML = `<div style="text-align:center;padding:30px;color:#6b7280;">No configs found in this subscription.<br><br><span style="font-size:12px;">The file may be empty or in an unsupported format.</span></div>`;
      return;
    }

    let html = "";
    // Client import row
    html += `<div class="rc-client-row">
      <span class="rc-client-label">Import to client:</span>`;
    for (const [key, fn] of Object.entries(CLIENT_LINKS)) {
      const link = fn(subUrl, subName);
      html += `<a href="${esc(link)}" class="rc-btn rc-btn-primary" style="text-transform:capitalize;" title="Import to ${esc(key)}">${esc(key)}</a>`;
    }
    html += `<button class="rc-btn rc-btn-secondary" id="rcCopySub">Copy URL</button>`;
    html += `</div>`;

    html += `<div style="font-size:11px;color:#6b7280;font-weight:700;text-transform:uppercase;letter-spacing:1px;margin-bottom:10px;">${configs.length} configs found</div>`;

    for (const cfg of configs.slice(0, 200)) {
      const qrUrl = QR_API + encodeURIComponent(cfg.raw);
      html += `
      <div class="rc-config-item">
        <div class="rc-config-qr"><img src="${esc(qrUrl)}" alt="qr" loading="lazy"></div>
        <div class="rc-config-info">
          <div class="rc-config-name">${esc(cfg.name)} <span style="color:#93c5fd;font-size:10px;text-transform:uppercase;">${esc(cfg.proto)}</span></div>
          <div class="rc-config-raw">${esc(cfg.raw.slice(0, 160))}</div>
          <div class="rc-config-actions">
            <button class="rc-btn rc-btn-primary" data-rc-copy="${esc(cfg.raw)}">Copy</button>
            <a href="${esc(qrUrl)}" target="_blank" class="rc-btn rc-btn-secondary">QR</a>
          </div>
        </div>
      </div>`;
    }
    if (configs.length > 200) {
      html += `<div style="text-align:center;padding:12px;color:#6b7280;font-size:12px;">... and ${configs.length - 200} more (showing first 200)</div>`;
    }
    modalBody.innerHTML = html;

    document.getElementById("rcCopySub")?.addEventListener("click", () => {
      copyText(subUrl, "Subscription URL copied");
    });
    modalBody.querySelectorAll("[data-rc-copy]").forEach((btn) => {
      btn.addEventListener("click", () => {
        copyText(btn.getAttribute("data-rc-copy"), "Config copied");
      });
    });
  };

  const showConfigs = async (subUrl, name) => {
    openModal(name || "Configs", subUrl);
    try {
      const text = await fetchSubscription(subUrl);
      const configs = parseSubscription(text);
      renderConfigs(configs, subUrl, name);
    } catch (e) {
      modalBody.innerHTML = `<div style="text-align:center;padding:30px;color:#f87171;">Failed to fetch: ${esc(e.message)}</div>
      <div style="text-align:center;padding:12px;">
        <a href="${esc(subUrl)}" target="_blank" class="rc-btn rc-btn-secondary">Open raw file</a>
        <button class="rc-btn rc-btn-secondary" id="rcRetryBtn" style="margin-left:8px;">Retry</button>
      </div>`;
      document.getElementById("rcRetryBtn")?.addEventListener("click", () => showConfigs(subUrl, name));
    }
  };

  // ---------- Browser-side ping ----------
  const pingHost = async (host, port) => {
    const url = `https://${host}:${port}/`;
    const samples = [];
    for (let i = 0; i < 3; i++) {
      const t0 = performance.now();
      try {
        await fetch(url + "?_=" + Date.now() + "-" + i, {
          mode: "no-cors",
          cache: "no-store",
          method: "HEAD",
        });
        const t1 = performance.now();
        samples.push(t1 - t0);
      } catch (e) {
        const t1 = performance.now();
        samples.push(t1 - t0);
      }
    }
    if (!samples.length) return null;
    samples.sort((a, b) => a - b);
    return samples[Math.floor(samples.length / 2)];
  };

  // ---------- Augment subscription cards ----------
  const augmentSubCard = (card) => {
    if (card.dataset.rcAugmented) return;
    const copyBtn = card.querySelector("[data-copy]");
    if (!copyBtn) return;
    const subUrl = copyBtn.getAttribute("data-copy");
    if (!subUrl || subUrl === "#" || subUrl.length < 10) return;
    const name = card.querySelector("h3")?.textContent?.trim() || "sub";

    const btn = document.createElement("button");
    btn.className = "btn btn-secondary rc-configs-btn";
    btn.textContent = "Show configs";
    btn.addEventListener("click", (e) => {
      e.preventDefault();
      showConfigs(subUrl, name);
    });
    card.appendChild(btn);
    card.dataset.rcAugmented = "1";
  };

  const augmentProxyCard = (card) => {
    if (card.dataset.rcPingAugmented) return;
    const mono = card.querySelector(".font-mono");
    if (!mono) return;
    const text = mono.textContent.trim();
    const m = text.match(/^([\w.\-]+):(\d+)/);
    if (!m) return;
    const host = m[1];
    const port = m[2];

    const dot = document.createElement("span");
    dot.className = "rc-ping-dot rc-ping-loading";
    dot.title = "Testing...";

    const label = document.createElement("span");
    label.textContent = "ping...";
    label.style.fontSize = "12px";
    label.style.color = "#9ca3af";
    label.style.fontFamily = '"JetBrains Mono", monospace';

    const wrap = document.createElement("span");
    wrap.style.display = "inline-flex";
    wrap.style.alignItems = "center";
    wrap.style.gap = "6px";
    wrap.style.marginLeft = "10px";
    wrap.appendChild(dot);
    wrap.appendChild(label);

    const pingRow = card.querySelector(".flex.items-center.gap-2.mt-3");
    if (pingRow) {
      pingRow.appendChild(wrap);
    }

    pingHost(host, port).then((rtt) => {
      dot.classList.remove("rc-ping-loading");
      if (rtt === null) {
        dot.classList.add("rc-ping-bad");
        label.textContent = "n/a";
        return;
      }
      const ms = Math.round(rtt);
      label.textContent = `${ms} ms`;
      if (ms < 150) dot.classList.add("rc-ping-good");
      else if (ms < 400) dot.classList.add("rc-ping-medium");
      else dot.classList.add("rc-ping-bad");
    });

    card.dataset.rcPingAugmented = "1";
  };

  // ---------- MutationObserver ----------
  const observe = () => {
    const subsGrid = document.getElementById("subsGrid");
    const proxiesList = document.getElementById("proxiesList");

    const scan = (root) => {
      if (!root) return;
      root.querySelectorAll(".card").forEach((c) => {
        if (c.closest("#subsGrid")) augmentSubCard(c);
        if (c.closest("#proxiesList")) augmentProxyCard(c);
      });
    };

    scan(subsGrid);
    scan(proxiesList);

    const mo = new MutationObserver((mutations) => {
      for (const mut of mutations) {
        for (const node of mut.addedNodes) {
          if (node.nodeType !== 1) continue;
          if (node.classList?.contains("card")) {
            if (node.closest("#subsGrid")) augmentSubCard(node);
            if (node.closest("#proxiesList")) augmentProxyCard(node);
          } else {
            scan(node.parentElement);
          }
        }
      }
    });

    if (subsGrid) mo.observe(subsGrid, { childList: true, subtree: true });
    if (proxiesList) mo.observe(proxiesList, { childList: true, subtree: true });
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", observe);
  } else {
    setTimeout(observe, 500);
  }
})();