### 🛠️ Advanced Capabilities
This repository now includes a robust backend processing pipeline:

1.  **Xray Manager**: Automated installation and configuration of Xray-core for deep packet inspection.
2.  **Data Processor**: 
    -   **Cleaner**: Validates URLs and removes malformed entries.
    -   **Fuzzy Matcher**: Detects near-duplicate proxies based on similarity algorithms.
    -   **Scorer**: Ranks proxies by latency, status, and source reliability.
3.  **Config Importer**: Support for importing Clash, V2Ray, and Surge configurations directly into our database.
4.  **Auto Maintainer**: Scheduled tasks for log rotation, data compression, and integrity checks.
5.  **Docker Support**: Full containerization with `Dockerfile` and `docker-compose.yml` for consistent environments.
6.  **CI/CD Automation**: Programmable management of GitHub Actions workflows, PRs, and Releases via Python scripts.
7.  **Local API Server**: Asynchronous server exposing proxy statistics and health metrics (`api_server.py`).
8.  **Deep Validation**: Advanced TLS fingerprinting and protocol-specific handshake simulation (`advanced_validator.py`).
9.  **Dashboard Generator**: Automated static HTML dashboard generation from raw JSON data (`dashboard_generator.py`).

---

## About the project