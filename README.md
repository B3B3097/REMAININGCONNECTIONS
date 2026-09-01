<div align="center">

# REMAININGCONNECTIONS

### Stay connected - it is not a choice, it is a necessity

[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-LIVE-success?style=for-the-badge&logo=github)](https://b3b3097.github.io/REMAININGCONNECTIONS/)
[![Telegram](https://img.shields.io/badge/Telegram-@REMAININGCONNECTIONS-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/REMAININGCONNECTIONS)
[![Solo Dev](https://img.shields.io/badge/made_by-solo_dev-orange?style=for-the-badge)](https://github.com/B3B3097)
[![License](https://img.shields.io/badge/license-MIT-blue?style=for-the-badge)](https://github.com/B3B3097/REMAININGCONNECTIONS)
[![Speed Test](https://img.shields.io/badge/Speed_Test-built_in-9333ea?style=for-the-badge)](https://b3b3097.github.io/REMAININGCONNECTIONS/)

**Subscriptions | TG Proxies | Open Source utilities | Speed Test | Auto-update 24/7**

[Dashboard](https://b3b3097.github.io/REMAININGCONNECTIONS/) |
[Speed Test](https://b3b3097.github.io/REMAININGCONNECTIONS/#tab-speedtest) |
[Bypass blocks](https://translate.google.com/translate?sl=en&tl=ru&u=https://b3b3097.github.io/REMAININGCONNECTIONS/) |
[Telegram](https://t.me/REMAININGCONNECTIONS)

</div>

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
- **Upload** - via `POST` with a generated payload
- **Progress** - animated speedometers and a live measurement log

Open the **Speed Test** tab on the dashboard and press **Start**.

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
            |  every 1-6 hours
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
|-- data/                 <- parser data (JSON)
|-- scripts/              <- Python generators
|-- .github/workflows/    <- automation (Actions)
```

---

## Automation

| Workflow | What it does | Schedule |
|----------|--------------|----------|
| Subscription Discovery | Search and validate subscriptions | every 2 hours |
| TG Proxy Discovery | Search and ping TG proxies | every hour |
| Utils Discovery | Search utilities (Android/iOS/Windows/Linux) | every 6 hours |
| Search Query Generator | Auto-generate search queries | every 6 hours |
| Enterprise Deploy | Build and deploy to GitHub Pages | on push to main |
| Export & Validate YAML | Export codebase.txt + YAML check | daily |

---

## Tech stack

- **Frontend:** HTML, Tailwind CSS (CDN), vanilla JavaScript (IIFE)
- **Backend / parsers:** Python 3.11 (requests, pyyaml), GitHub Actions
- **Hosting:** GitHub Pages (static, free)
- **Data sources:** GitHub API, Gitverse API, raw.githubusercontent.com
- **Speed Test:** native `fetch` + Performance API, no third-party services

---

## Roadmap

- [x] Dashboard on GitHub Pages
- [x] Auto-parsers for subscriptions, proxies, utilities
- [x] Block bypass via Google Translate
- [x] Built-in Speed Test (ping, jitter, download, upload)
- [ ] Telegram notifications
- [ ] Speed measurement history

---

## Links

- **Site:** [b3b3097.github.io/REMAININGCONNECTIONS](https://b3b3097.github.io/REMAININGCONNECTIONS/)
- **Speed Test:** [tab on the dashboard](https://b3b3097.github.io/REMAININGCONNECTIONS/#tab-speedtest)
- **Telegram:** [@REMAININGCONNECTIONS](https://t.me/REMAININGCONNECTIONS)
- **GitHub:** [@B3B3097](https://github.com/B3B3097)

---

<div align="center">

**Stay connected - it is not a choice, it is a necessity.**

</div>