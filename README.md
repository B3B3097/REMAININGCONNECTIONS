# 🌐 REMAININGCONNECTIONS

> **Автоматизированный комплекс для непрерывного поиска, криптографической валидации и 24/7 мониторинга Telegram MTProto прокси и сетевых подписок V2Ray/Xray.**

Система автоматически сканирует открытые репозитории GitHub, извлекает сетевые конфигурации, проводит глубокое тестирование протоколов на уровне рукопожатия Telegram DC и формирует готовые к использованию списки прокси во всех популярных форматах.

---

## 🔗 Быстрый доступ и ресурсы

<p align="center">
  <a href="https://b3b3097.github.io/REMAININGCONNECTIONS/" target="_blank">
    <img src="https://img.shields.io/badge/Live_Dashboard-GitHub_Pages-22c55e?style=for-the-badge&logo=github&logoColor=white" alt="Live Dashboard"/>
  </a>
  <a href="https://t.me/REMAININGCONNECTIONS" target="_blank">
    <img src="https://img.shields.io/badge/Telegram-Канал_Прокси-0284c7?style=for-the-badge&logo=telegram&logoColor=white" alt="Telegram"/>
  </a>
  <a href="https://remainconnected.vercel.app/" target="_blank">
    <img src="https://img.shields.io/badge/Web_Mirror-Vercel-000000?style=for-the-badge&logo=vercel&logoColor=white" alt="Vercel Mirror"/>
  </a>
</p>

<p align="center">
  <img src="https://img.shields.io/github/actions/workflow/status/B3B3097/REMAININGCONNECTIONS/tg-proxy-discovery.yml?label=TG%20Proxy%20Discovery&style=flat-square" alt="TG Proxy Discovery"/>
  <img src="https://img.shields.io/github/actions/workflow/status/B3B3097/REMAININGCONNECTIONS/subscription-discovery.yml?label=Subscriptions%20Discovery&style=flat-square" alt="Subscriptions Discovery"/>
  <img src="https://img.shields.io/github/actions/workflow/status/B3B3097/REMAININGCONNECTIONS/deploy.yml?label=Dashboard%20Deploy&style=flat-square" alt="Dashboard Deploy"/>
  <img src="https://img.shields.io/badge/Data%20Update-Every%20Hour-blue?style=flat-square" alt="Update Frequency"/>
</p>

---

## ⚡ Ключевые возможности

### 🔐 Глубокая криптографическая проверка MTProto
- **Obfuscated2 + FakeTLS**: Полная эмуляция TLS 1.3 ClientHello с корректным расчётом HMAC и поддержкой SNI-доменов (Cloudflare, Google, Yandex и др.).
- **Telegram DC Handshake**: Отправка `req_pq_multi` непосредственно в дата-центры Telegram (DC 1, DC 2, DC 4, DC 5) с валидацией ответа `resPQ` (`0x05162463`).
- **Быстрый TCP Pre-check**: Моментальное отсечение недоступных хостов без зависаний тайм-аута.
- **Поддержка всех типов секретов**: Обычный 16-байтный hex, `dd`-префиксы (secure mode), `ee`-префиксы (FakeTLS + домен), а также Base64 / Base64URL форматы.

### 📡 Подписки V2Ray / Xray / VPN
- Сканирование и парсинг публичных подписок GitHub.
- Поддержка протоколов: `vless://`, `vmess://`, `trojan://`, `ss://`, `ssr://`, `hysteria://`.
- Контроль дубликатов и очистка от нерабочих конфигураций.

### 📦 Экспорт в 1 клик
Все списки регулярно обновляются в папке [`exports/`](./exports/):
| Формат | Файл | Описание |
|---|---|---|
| 🔗 **Telegram Links** | [`exports/telegram_links.txt`](./exports/telegram_links.txt) | Прямые ссылки `tg://proxy?server=...` для подключения в 1 клик |
| 📋 **Simple List** | [`exports/telegram_simple.txt`](./exports/telegram_simple.txt) | Список формата `host:port:secret` |
| 🏷️ **Protocol Format** | [`exports/telegram_protocol.txt`](./exports/telegram_protocol.txt) | Список формата `mtproto://secret@host:port` |
| 📊 **CSV Report** | [`exports/telegram_proxies.csv`](./exports/telegram_proxies.csv) | Таблица с задержками (latency), DC и статусом |
| 📄 **Full Details** | [`exports/telegram_detailed.txt`](./exports/telegram_detailed.txt) | Детальный отчёт с метаданными валидации |

---

## 📊 Структура данных

Результаты проверок хранятся в формате JSON в директории `data/`:
- `data/tg_proxies_found.json` — Все найденные и протестированные Telegram MTProto прокси с параметрами `status`, `latency_ms`, `dc_connected`, `verification`.
- `data/subscriptions_found.json` — Обнаруженные подписки и узлы Xray/V2Ray.
- `data/summary.json` — Агрегированная сводка по всем категориям и общее количество активных прокси.

---

## 🚀 Использование прокси в Telegram

1. Откройте [`exports/telegram_links.txt`](./exports/telegram_links.txt) или зайдите на [онлайн-дашборд](https://b3b3097.github.io/REMAININGCONNECTIONS/).
2. Нажмите на ссылку любого активного прокси (зелёный статус, низкий пинг).
3. В открывшемся Telegram нажмите **«Включить прокси» (Enable Proxy)**.

---

## 🤖 GitHub Actions Автоматизация

Сбор и валидация выполняются независимыми воркфлоу по расписанию:
- **`TG Proxy Discovery`** (`.github/workflows/tg-proxy-discovery.yml`): Каждый час — извлечение новых прокси, строгая валидация MTProto рукопожатия и коммит результатов.
- **`Subscription Discovery`** (`.github/workflows/subscription-discovery.yml`): Поиск и проверка V2Ray подписок.
- **`Generate Summary Report`** (`.github/workflows/generate-summary.yml`): Сборка единого файла статистики `data/summary.json`.
- **`Export Proxy Formats`** (`.github/workflows/export-formats.yml`): Генерация файлов в папке `exports/`.
- **`Deploy to GitHub Pages`** (`.github/workflows/deploy.yml`): Сборка дашборда и публикация на GitHub Pages.

---

## 💻 Локальный запуск и разработка

```bash
# Клонирование репозитория
git clone https://github.com/B3B3097/REMAININGCONNECTIONS.git
cd REMAININGCONNECTIONS

# Установка зависимостей
pip install -r requirements.txt

# Проверка конкретного MTProto прокси
python scripts/mtproto_real_checker.py --host 109.107.166.49 --port 443 --secret a4bc6821c58eee9b48038b104950504a

# Полная валидация извлеченных прокси
python scripts/check_tg_proxies.py --input extracted/tg_proxies_extracted.json --output checked/tg_proxies_checked.json --enable-mtproto

# Экспорт форматов
python scripts/export_formats.py
```

---

## 📄 Лицензия

Проект распространяется под лицензией MIT. Исходные коды открыты для свободного использования и модификации.
