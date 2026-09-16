 # 📡 REMAININGCONNECTIONS API Documentation

## Обзор

Все данные хранятся в JSON-файлах в директории `data/` и обновляются автоматически через GitHub Actions.

---

## 🔗 Endpoints (Static Files)

### Base URL
```
https://raw.githubusercontent.com/B3B3097/REMAININGCONNECTIONS/main/data/
```

### Available Endpoints

| Endpoint | Description | Update Frequency |
|----------|-------------|------------------|
| `subscriptions_found.json` | VLESS/VMess/Trojan subscriptions | Every hour |
| `tg_proxies_found.json` | Telegram MTProto proxies | Every hour |
| `http_proxies_found.json` | HTTP/HTTPS proxies | Every 2 hours |
| `socks_proxies_found.json` | SOCKS4/5 proxies | Every 2 hours |
| `utils_found.json` | Utility configurations | Every 4 hours |
| `summary.json` | Overall statistics | Every 6 hours |

---

## 📊 Data Schemas

### HTTP/SOCKS Proxies

```json
{
  "generated_at": "2024-01-15T12:00:00Z",
  "total_checked": 500,
  "total_working": 150,
  "success_rate": 30.0,
  "proxies": [
    {
      "host": "192.168.1.1",
      "port": 1080,
      "protocol": "socks5",
      "type": "socks5",
      "latency_ms": 125.5,
      "status": "working",
      "verified_at": "2024-01-15T12:00:00Z",
      "source": "owner/repo"
    }
  ]
}
```

### Telegram Proxies

```json
{
  "generated_at": "2024-01-15T12:00:00Z",
  "total_working": 50,
  "proxies": [
    {
      "host": "192.168.1.1",
      "port": 443,
      "secret": "abcdef1234567890",
      "protocol": "mtproto",
      "type": "telegram",
      "latency_ms": 85.3,
      "status": "working",
      "verified_at": "2024-01-15T12:00:00Z",
      "source": "owner/repo",
      "tg_link": "tg://proxy?server=192.168.1.1&port=443&secret=abcdef1234567890"
    }
  ]
}
```

### Summary

```json
{
  "generated_at": "2024-01-15T12:00:00Z",
  "categories": {
    "subscriptions": {
      "count": 120,
      "last_updated": "2024-01-15T11:00:00Z",
      "file": "data/subscriptions_found.json"
    },
    "telegram": {
      "count": 50,
      "last_updated": "2024-01-15T10:00:00Z",
      "file": "data/tg_proxies_found.json"
    },
    "http": {
      "count": 80,
      "last_updated": "2024-01-15T09:00:00Z",
      "file": "data/http_proxies_found.json"
    },
    "socks": {
      "count": 70,
      "last_updated": "2024-01-15T09:00:00Z",
      "file": "data/socks_proxies_found.json"
    },
    "utilities": {
      "count": 15,
      "last_updated": "2024-01-15T08:00:00Z",
      "file": "data/utils_found.json"
    }
  },
  "total_proxies": 335
}
```

---

## 🔍 Usage Examples

### Python

```python
import requests

# Fetch HTTP proxies
response = requests.get(
    'https://raw.githubusercontent.com/B3B3097/REMAININGCONNECTIONS/main/data/http_proxies_found.json'
)
data = response.json()

# Get working proxies sorted by latency
proxies = sorted(data['proxies'], key=lambda p: p['latency_ms'])
fastest = proxies[0]
print(f"Fastest: {fastest['host']}:{fastest['port']} ({fastest['latency_ms']}ms)")
```

### cURL

```bash
# Download all data
curl -o summary.json \
  https://raw.githubusercontent.com/B3B3097/REMAININGCONNECTIONS/main/data/summary.json

# Extract proxy count
curl -s https://raw.githubusercontent.com/B3B3097/REMAININGCONNECTIONS/main/data/http_proxies_found.json \
  | jq '.total_working'

# Get fastest 10 proxies
curl -s https://raw.githubusercontent.com/B3B3097/REMAININGCONNECTIONS/main/data/socks_proxies_found.json \
  | jq '.proxies | sort_by(.latency_ms) | .[0:10]'
```

### JavaScript

```javascript
// Fetch summary
fetch('https://raw.githubusercontent.com/B3B3097/REMAININGCONNECTIONS/main/data/summary.json')
  .then(res => res.json())
  .then(data => {
    console.log(`Total proxies: ${data.total_proxies}`);
    Object.entries(data.categories).forEach(([cat, info]) => {
      console.log(`${cat}: ${info.count}`);
    });
  });
```

---

## 🔧 Filtering & Sorting

### By Protocol

```bash
# HTTP only
jq '.proxies[] | select(.protocol == "http")' data/http_proxies_found.json

# SOCKS5 only
jq '.proxies[] | select(.protocol == "socks5")' data/socks_proxies_found.json
```

### By Latency

```bash
# Under 100ms
jq '.proxies[] | select(.latency_ms < 100)' data/http_proxies_found.json

# Fastest 5
jq '.proxies | sort_by(.latency_ms) | .[0:5]' data/socks_proxies_found.json
```

### By Source

```bash
# From specific repo
jq '.proxies[] | select(.source | contains("specific-repo"))' data/http_proxies_found.json
```

---

## 📝 Field Descriptions

### Common Fields

- `generated_at` (string): ISO 8601 timestamp when data was generated
- `total_working` (integer): Number of validated working proxies
- `total_checked` (integer): Total proxies checked during validation
- `success_rate` (float): Percentage of working proxies

### Proxy Object

- `host` (string): IP address or hostname
- `port` (integer): Port number (1-65535)
- `protocol` (string): Protocol type (http, https, socks4, socks5, mtproto)
- `type` (string): Proxy type (same as protocol)
- `latency_ms` (float): Response latency in milliseconds
- `status` (string): Validation status (always "working" in output)
- `verified_at` (string): ISO 8601 timestamp of last verification
- `source` (string): GitHub repository where proxy was found
- `secret` (string, Telegram only): MTProto secret
- `tg_link` (string, Telegram only): Ready-to-use Telegram proxy link

---

## ⚡ Rate Limits

Static files on GitHub have no official rate limits, but consider:

- **Recommended**: Cache responses for 5-10 minutes
- **Maximum**: Poll once per minute per file
- **Best practice**: Use GitHub's ETags for conditional requests

### Conditional Requests Example

```python
import requests

session = requests.Session()
url = 'https://raw.githubusercontent.com/B3B3097/REMAININGCONNECTIONS/main/data/summary.json'

# First request
response = session.get(url)
etag = response.headers.get('ETag')

# Subsequent requests
response = session.get(url, headers={'If-None-Match': etag})
if response.status_code == 304:
    print("Data not modified")
else:
    data = response.json()
```

---

## 🔐 Security Notes

- All data is **read-only** and publicly accessible
- No authentication required
- Data comes from public GitHub repositories
- Always validate proxies yourself before use
- Monitor for malicious proxies (rare but possible)

---

## 📞 Support

- Issues: https://github.com/B3B3097/REMAININGCONNECTIONS/issues
- Discussions: https://github.com/B3B3097/REMAININGCONNECTIONS/discussions
- Telegram: [@REMAININGCONNECTIONS](https://t.me/REMAININGCONNECTIONS)