<div align="center">

# REMAININGCONNECTIONS

### Stay connected - it is not a choice, it is a necessity

[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-LIVE-success?style=for-the-badge&logo=github)](https://b3b3097.github.io/REMAININGCONNECTIONS/)
[![Telegram](https://img.shields.io/badge/Telegram-@REMAININGCONNECTIONS-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/REMAININGCONNECTIONS)
[![Solo Dev](https://img.shields.io/badge/made_by-solo_dev-orange?style=for-the-badge)](https://github.com/B3B3097)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](https://github.com/B3B3097/REMAININGCONNECTIONS)
[![Speed Test](https://img.shields.io/badge/Speed_Test-built_in-9333ea?style=for-the-badge)](https://b3b3097.github.io/REMAININGCONNECTIONS/)
[![Auto Update](https://img.shields.io/badge/Auto_Update-Every_Hour-brightgreen?style=for-the-badge)](https://github.com/B3B3097/REMAININGCONNECTIONS/actions)

**Subscriptions | TG Proxies | Open Source utilities | Speed Test | Auto-update 24/7**

[Dashboard](https://b3b3097.github.io/REMAININGCONNECTIONS/) |
[Speed Test](https://b3b3097.github.io/REMAININGCONNECTIONS/#tab-speedtest) |
[Bypass blocks](https://translate.google.com/translate?sl=en&tl=ru&u=https://b3b3097.github.io/REMAININGCONNECTIONS/) |
[Telegram](https://t.me/REMAININGCONNECTIONS)

</div>

---

## 🎉 Latest Updates (2024)

### ✨ New Features
- ⚡ **Faster updates**: All workflows now run **every hour** (was: 2-6 hours)
- 🔧 **Speed Test Upload fixed**: Now accurately measures upload speed using XHR progress tracking
- 📊 Real-time upload progress visualization in Speed Test
- 🚀 Improved workflow scheduling to avoid API rate limits

### 📝 Documentation
- Added `SPEED_TEST_FIX.md` — detailed guide for Speed Test upload fix
- Added `FIXES_SUMMARY.md` — complete changelog and recommendations
- Added `docs/speedtest-fix.js` — ready-to-use upload measurement code

---

## About the project

**REMAININGCONNECTIONS** is an automated monitoring system for censorship-circumvention tools and connection-quality checks.

It works autonomously, without human intervention:

- **Finds** subscriptions (VLESS, VMESS, Shadowsocks, Trojan, Hysteria2, TUIC, WireGuard) on GitHub and Gitverse
- **Collects** working Telegram MTProto proxies
- **Detects** verified Open Source utilities and clients for all platforms
- **Validates** freshness: last commit, number of configs, BS/CS status, ping
- **Measures** internet speed right in the browser - download, upload, ping, jitter
- **Displays** everything on a live dashboard with filters, search and sorting

---

## Speed Test

The built-in internet speed test runs entirely in the browser, with no server-side component:

- **Ping (RTT)** - via `fetch` to a small file, multiple samples
- **Jitter** - ping variation between requests
- **Download** - through a large payload fetch, Mbit/s calculation
- **Upload** - via `XMLHttpRequest` with real-time progress tracking (fixed in 2024)
- **Progress** - animated speedometers and a live measurement log

Open the **Speed Test** tab on the dashboard and press **Start**.

### 🔧 Speed Test Upload Fix Applied
The upload measurement now uses `XMLHttpRequest` instead of `fetch()` API to accurately track data transmission progress. This provides:
- ✅ Real upload speed (not instant completion)
- ✅ Animated speedometer during upload
- ✅ Progress logs with intermediate values
- ✅ Accurate Mbps calculation

See `SPEED_TEST_FIX.md` for technical details.

---

## About the developer

The project is built by a **single person** - a solo developer.

All code, parsers, dashboard, automation and design are done manually, without a team or budget.

---

## How it works

```
GitHub / Gitverse / Telegram
            |
            v
   GitHub Actions (parsers)
            |  every 1 hour ⚡ NEW
            v
      data/*.json (data)
            |
            v
   docs/index.html (dashboard)
            |
            v
      GitHub Pages (site)
            |
            v
   User + Speed Test
```

---

## Structure

```
REMAININGCONNECTIONS/
|-- docs/
|   |-- index.html        <- dashboard + Speed Test
|   |-- speedtest-fix.js  <- upload fix (NEW)
|-- data/                 <- parser data (JSON)
|-- scripts/              <- Python generators
|-- .github/workflows/    <- automation (Actions)
|-- SPEED_TEST_FIX.md     <- upload fix documentation (NEW)
|-- FIXES_SUMMARY.md      <- complete changelog (NEW)
```

---

## Automation

| Workflow | What it does | Schedule | Status |
|----------|--------------|----------|--------|
| Subscription Discovery | Search and validate subscriptions | **every hour** ⚡ | ✅ Updated |
| TG Proxy Discovery | Search and ping TG proxies | every hour | ✅ Active |
| Utils Discovery | Search utilities (Android/iOS/Windows/Linux) | **every hour** ⚡ | ✅ Updated |
| Search Query Generator | Auto-generate search queries | **every hour** ⚡ | ✅ Updated |
| Enterprise Deploy | Build and deploy to GitHub Pages | on push to main | ✅ Active |
| Export & Validate YAML | Export codebase.txt + YAML check | daily | ✅ Active |

⚡ = Updated to run more frequently (was: 2-6 hours)

### ⚠️ GitHub Actions Usage Note
With all workflows running every hour, the monthly usage will be approximately **18,000-72,000 minutes** depending on execution time. The free GitHub tier provides **2,000 minutes/month**. Consider:
- Using a paid GitHub plan ($4/month for 3,000 additional minutes)
- Reducing workflow frequency (e.g., every 2-3 hours)
- Lowering `max_repos` and `max_probe` limits in workflow inputs

See `FIXES_SUMMARY.md` for detailed recommendations.

---

## Tech stack

- **Frontend:** HTML, Tailwind CSS (CDN), vanilla JavaScript (IIFE)
- **Backend / parsers:** Python 3.11 (requests, pyyaml), GitHub Actions
- **Hosting:** GitHub Pages (static, free)
- **Data sources:** GitHub API, Gitverse API, raw.githubusercontent.com
- **Speed Test:** native `fetch` + `XMLHttpRequest` + Performance API, no third-party services

---

## Roadmap

- [x] Dashboard on GitHub Pages
- [x] Auto-parsers for subscriptions, proxies, utilities
- [x] Block bypass via Google Translate
- [x] Built-in Speed Test (ping, jitter, download, upload)
- [x] Speed Test upload fix with XHR progress tracking ⚡ NEW
- [x] Hourly auto-updates for all workflows ⚡ NEW
- [ ] Telegram notifications
- [ ] Speed measurement history
- [ ] Custom domain with blocking bypass

---

## Bypass Blocking

### Option 1: Google Translate Proxy (built-in)
```
https://translate.google.com/translate?sl=en&tl=ru&u=https://b3b3097.github.io/REMAININGCONNECTIONS/
```
⚠️ May be slow or unreliable

### Option 2: Cloudflare Workers (recommended, free)
Deploy a simple proxy worker:
```javascript
addEventListener('fetch', event => {
  event.respondWith(handleRequest(event.request))
})

async function handleRequest(request) {
  const url = new URL(request.url)
  const targetUrl = 'https://b3b3097.github.io' + url.pathname
  const response = await fetch(targetUrl)
  return new Response(response.body, response)
}
```
Access via: `https://your-worker.workers.dev`

### Option 3: Custom Domain
1. Buy a cheap domain (~$1/year on Namecheap)
2. GitHub Settings → Pages → Custom domain
3. Free SSL certificate from GitHub

See `FIXES_SUMMARY.md` for detailed instructions.

---

## Links

- **Site:** [b3b3097.github.io/REMAININGCONNECTIONS](https://b3b3097.github.io/REMAININGCONNECTIONS/)
- **Speed Test:** [tab on the dashboard](https://b3b3097.github.io/REMAININGCONNECTIONS/#tab-speedtest)
- **Telegram:** [@REMAININGCONNECTIONS](https://t.me/REMAININGCONNECTIONS)
- **GitHub:** [@B3B3097](https://github.com/B3B3097)

---

## Contributing

This is a solo project, but suggestions and bug reports are welcome via Issues.

---

<div align="center">

**Stay connected - it is not a choice, it is a necessity.**

Made with 💙 by a solo developer | 2024

</div>