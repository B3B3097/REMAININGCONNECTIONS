 # 🌐 REMAININGCONNECTIONS

> **Автоматизированный комплекс для поиска, валидации и мониторинга прокси-соединений из открытых источников GitHub.**

Проект предназначен для глубокого анализа сетевой инфраструктуры, автоматического извлечения прокси-конфигураций из публичных репозиториев GitHub, их валидации и мониторинга производительности. Система полностью автоматизирована и работает 24/7 через GitHub Actions.

---

## 🔗 Официальные ресурсы

<p align="center">
  <a href="https://t.me/REMAININGCONNECTIONS" target="_blank">
    <img src="https://img.shields.io/badge/Telegram-%40REMAININGCONNECTIONS-blue?style=for-the-badge&logo=telegram" alt="Telegram"/>
  </a>
  <a href="https://remainconnected.vercel.app/" target="_blank">
    <img src="https://img.shields.io/badge/Web_Mirror-remainconnected-vercel?style=for-the-badge&logo=vercel" alt="Web Mirror"/>
  </a>
  <a href="https://b3b3097.github.io/REMAININGCONNECTIONS/" target="_blank">
     <img src="https://img.shields.io/badge/Dashboard-GitHub_Pages-green?style=for-the-badge&logo=github" alt="Dashboard"/>
  </a>
</p>

---

## ✨ Ключевые возможности

### 🔍 Автоматическое обнаружение

*   **GitHub Code Search**: Автоматический поиск прокси-конфигураций в публичных репозиториях
*   **Multi-Protocol Support**: VLESS, VMess, Trojan, Shadowsocks, HTTP, HTTPS, SOCKS4/5, Telegram MTProto
*   **Smart Extraction**: Парсинг различных форматов (subscription links, base64, JSON, plain text)
*   **Deduplication**: Интеллектуальное устранение дубликатов

### ✅ Глубокая валидация

*   **Real Connection Testing**: Проверка фактической доступности через прямое подключение
*   **Protocol Verification**: Валидация специфичных протоколов (MTProto, SOCKS)
*   **Latency Measurement**: Измерение времени отклика для каждого прокси
*   **Rate Limiting**: Контроль нагрузки при валидации

### 📊 Мониторинг и аналитика

*   **Real-time Stats**: Динамическое обновление статистики каждые 1-6 часов
*   **Success Rate Tracking**: Отслеживание процента работающих прокси
*   **Source Attribution**: Информация об источнике каждого прокси
*   **Historical Data**: Сохранение результатов проверок для анализа трендов

### 🤖 Полная автоматизация

*   **GitHub Actions Workflows**: 6 независимых pipeline для разных типов прокси
*   **Scheduled Runs**: Автоматический запуск по расписанию
*   **Auto-commit**: Автоматическая фиксация результатов в репозиторий
*   **Error Handling**: Graceful degradation при ошибках

---

## 🛠 Технический стек

*   **Backend**: Python 3.11+ (Asyncio, AIOHTTP, aiohttp-socks)
*   **Validation**: Custom TCP/TLS Validators, Xray-core compatibility
*   **Data Processing**: JSON, Base64, YAML parsing
*   **CI/CD**: GitHub Actions (6 workflows), scheduled cron jobs
*   **Frontend**: Static site generation (TailwindCSS, Chart.js)

---

## 📂 Структура проекта

```
REMAININGCONNECTIONS/
├── .github/workflows/          # GitHub Actions workflows
│   ├── subscription-discovery.yml    # VLESS/VMess/Trojan discovery
│   ├── tg-proxy-discovery.yml        # Telegram MTProto discovery
│   ├── http-socks-discovery.yml      # HTTP/SOCKS discovery
│   ├── utils-discovery.yml           # Utilities discovery
│   ├── generate-summary.yml          # Summary generation
│   └── validate-data.yml             # Data validation
├── scripts/                    # Extraction and validation scripts
│   ├── extract_tg_proxies.py         # Telegram proxy extractor
│   ├── extract_http_socks_proxies.py # HTTP/SOCKS extractor
│   ├── validate_http_socks_proxies.py # HTTP/SOCKS validator
│   ├── check_tg_proxies.py           # Telegram validator
│   ├── generate_summary.py           # Summary generator
│   └── strict_proxy_checker.py       # Xray protocol validator
├── data/                       # Output data (auto-updated)
│   ├── subscriptions_found.json      # VLESS/VMess/Trojan proxies
│   ├── tg_proxies_found.json         # Telegram proxies
│   ├── http_proxies_found.json       # HTTP/HTTPS proxies
│   ├── socks_proxies_found.json      # SOCKS4/5 proxies
│   ├── utils_found.json              # Utility configurations
│   └── summary.json                  # Overall statistics
├── extracted/                  # Raw extracted data
└── checked/                    # Validation results
```

---

## 🚀 Быстрый старт

### Локальный запуск

```bash
# Клонировать репозиторий
git clone https://github.com/B3B3097/REMAININGCONNECTIONS.git
cd REMAININGCONNECTIONS

# Установить зависимости
pip install -r requirements.txt

# Извлечь Telegram прокси
export GITHUB_TOKEN=your_github_token
python scripts/extract_tg_proxies.py

# Валидировать прокси
python scripts/validate_http_socks_proxies.py \
  --input extracted/http_proxies_extracted.json \
  --output data/http_proxies_found.json \
  --protocols http https \
  --concurrency 50

# Сгенерировать сводку
python scripts/generate_summary.py
```

### Автоматический режим (GitHub Actions)

Все воркфлоу настроены на автоматический запуск:

- **Subscription Discovery**: каждый час (`:40`)
- **TG Proxy Discovery**: каждый час (`:10`)
- **HTTP/SOCKS Discovery**: каждые 2 часа (`:25`)
- **Utils Discovery**: каждые 4 часа (`:55`)
- **Summary Generation**: каждые 6 часов + после каждого discovery
- **Data Validation**: ежедневно в 00:00 UTC

Также доступен ручной запуск через `workflow_dispatch`.

---

## 📊 Форматы данных

### Структура output JSON

```json
{
  "generated_at": "2024-01-15T12:00:00Z",
  "total_working": 150,
  "total_checked": 500,
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

---

## 🔧 Конфигурация

### Переменные окружения

- `GITHUB_TOKEN` - токен для доступа к GitHub API (опционально, но рекомендуется)
- `CONCURRENCY_LIMIT` - лимит параллельных проверок (default: 30-50)
- `MAX_CHECK_PROXIES` - максимум прокси для проверки (default: 1000-2000)

### Настройка workflow

Все параметры можно передать через `workflow_dispatch` inputs:

```yaml
workflow_dispatch:
  inputs:
    max_check:
      description: 'Max proxies to check'
      default: '1000'
    concurrency_limit:
      description: 'Concurrency limit'
      default: '50'
```

---

## 📈 Мониторинг

### Просмотр статистики

```bash
# Вывести сводку
cat data/summary.json | jq

# Проверить количество работающих прокси
jq '.total_working' data/http_proxies_found.json

# Найти самые быстрые прокси
jq '.proxies | sort_by(.latency_ms) | .[0:10]' data/socks_proxies_found.json
```

### GitHub Actions

Все запуски можно отслеживать в разделе Actions репозитория:
https://github.com/B3B3097/REMAININGCONNECTIONS/actions

---

## 🤝 Вклад в проект

Приветствуются:
- Новые источники прокси
- Улучшения алгоритмов валидации
- Оптимизация производительности
- Документация и примеры

### Как добавить новый источник

1. Добавьте поисковый запрос в `SEARCH_QUERIES` в соответствующем extractor
2. Протестируйте локально
3. Создайте Pull Request

---

## 📝 Лицензия

MIT License - см. [LICENSE](LICENSE)

---

## ⚠️ Disclaimer

Этот проект создан исключительно для образовательных целей и исследования публично доступных данных. Пользователи несут полную ответственность за соблюдение законов и правил использования прокси-серверов в своих юрисдикциях.

**Использование прокси может нарушать:**
- Условия использования некоторых сервисов
- Местное законодательство о конфиденциальности
- Правила обхода блокировок

Автор не несет ответственности за использование этого инструмента в незаконных целях.

---

## 📞 Контакты

- **Telegram**: [@REMAININGCONNECTIONS](https://t.me/REMAININGCONNECTIONS)
- **GitHub Issues**: [Сообщить о проблеме](https://github.com/B3B3097/REMAININGCONNECTIONS/issues)
- **GitHub Discussions**: [Обсудить проект](https://github.com/B3B3097/REMAININGCONNECTIONS/discussions)

---

<p align="center">
  <sub>Разработано с ❤️ для сообщества</sub>
</p>