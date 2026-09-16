# REMAININGCONNECTIONS: Advanced Features & Integration Guide

This document outlines the advanced capabilities integrated into the REMAININGCONNECTIONS project. These features enhance automation, reliability, and data quality for censorship-circumvention tools.

## 1. Xray Core Integration

We have introduced native support for Xray-core verification within our workflows. This allows us to validate proxies through a real-world tunnel simulation rather than just TCP handshakes.

### How it works
1. **Workflow Trigger**: The `tg-proxy-discovery.yml` workflow now includes an optional input `enable_xray`.
2. **Installation**: When enabled, the workflow uses `scripts/xray_manager.py` to download and install the latest stable Xray binary.
3. **Verification**: Proxies with URIs are tested via the Xray core. Results are merged back into the main JSON payload.

### Configuration
Xray behavior can be tuned using the configuration file located at `configs/xray_config.json`.
*   **Log Level**: Set to `warning` by default to reduce noise.
*   **Outbounds**: Supports VMess, VLESS, Trojan, and Shadowsocks.
*   **Routing**: Includes basic rules to bypass private IPs and block ads.

## 2. MTProto Proxy Checker

Telegram MTProto proxies often require secret validation to ensure they are functional and not just open ports. We have implemented a full protocol handshake checker.

### Features
*   **Handshake Simulation**: Mimics the Telegram client's initial connection sequence.
*   **Secret Validation**: Decodes hex secrets and verifies their length and format.
*   **DC Connectivity**: Checks if the proxy can reach Telegram's data centers.

### Usage
Run manually or via CLI:
```bash
python3 scripts/telegram_mtproto_checker.py --host 1.2.3.4 --port 443 --secret <hex_secret>
```

## 3. Health Monitoring & Alerting System

A dedicated monitoring service runs every 30 minutes to track the health of our proxy database.

### Metrics Tracked
*   **Success Rate**: Percentage of working proxies. Alerts trigger if this drops below 10%.
*   **Latency**: Average response time. Alerts trigger if average latency exceeds 2 seconds.
*   **Volume**: Monitors the total number of active proxies found.

### Logging
Metrics are saved to `data/health_metrics.json` (history) and `data/monitoring_alerts.log` (events).

## 4. Data Processing Pipeline

To improve data quality, we've added a robust processing layer.

### Components
*   **Data Cleaner**: Validates URLs, removes malformed entries, and standardizes formats.
*   **Fuzzy Matcher**: Detects near-duplicates that differ slightly in parameters.
*   **Proxy Scorer**: Ranks proxies based on status, latency, source popularity, and protocol efficiency.
*   **Merger**: Combines subscriptions, proxies, and utils into a single unified dataset.

### Running the Processor
```bash
python3 scripts/data_processor.py
```
This generates `ranked_proxies.json` and a summary report.

## 5. Automated Maintenance

The `scripts/auto_maintainer.py` script ensures the repository remains clean and efficient.

### Capabilities
*   **Log Rotation**: Cleans up old temporary files.
*   **Git Hygiene**: Automates commits for generated data.
*   **Stats Report**: Generates a text-based summary of the repository's current state.

---

## Roadmap

*   [ ] **Cloudflare Worker Integration**: Add support for CF workers as transport protocols.
*   [ ] **UI Dashboard Update**: Visualize the new health metrics on the GitHub Pages dashboard.
*   [ ] **Multi-threaded Speed Test**: Implement parallel speed testing for higher throughput.

---
*Last Updated: $(date +%Y-%m-%d)*