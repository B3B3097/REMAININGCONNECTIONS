
```markdown
<div align="center">

<img src="docs/assets/logo.png" alt="Остаться на связи" width="220">

# 🛜 REMAININGCONNECTIONS

### Остаться на связи — это не выбор, это необходимость

[![GitHub Pages](https://img.shields.io/badge/GitHub_Pages-LIVE-success?style=for-the-badge&logo=github)](https://b3b3097.github.io/REMAININGCONNECTIONS/)
[![Telegram](https://img.shields.io/badge/Telegram-@REMAININGCONNECTIONS-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/REMAININGCONNECTIONS)
[![Solo Dev](https://img.shields.io/badge/сделано-одним_разработчиком-orange?style=for-the-badge)](https://github.com/B3B3097)

**Подписки · ТГ Прокси · Open Source утилиты · Автообновление 24/7**

[🌐 Открыть дашборд](https://b3b3097.github.io/REMAININGCONNECTIONS/) ·
[🛡️ Обход блокировок](https://translate.google.com/translate?sl=en&tl=ru&u=https://b3b3097.github.io/REMAININGCONNECTIONS/) ·
[📱 Telegram](https://t.me/REMAININGCONNECTIONS)

</div>

---

## 📖 Что это за проект

**REMAININGCONNECTIONS** — автоматическая система мониторинга средств обхода блокировок.

Она сама, без участия человека:

- 🔍 **Ищет** подписки (VLESS, VMESS, Shadowsocks, Trojan, Hysteria2, TUIC, WireGuard) на GitHub и Gitverse
- 📡 **Собирает** рабочие Telegram-прокси (MTProto)
- 🛠️ **Находит** проверенные Open Source утилиты и клиенты
- ✅ **Проверяет** актуальность: последний коммит, количество конфигов, статус БС/ЧС
- 📊 **Выводит** всё на живой дашборд

---

## 👨💻 О разработчике

Проект делает **один человек** — соло-разработчик.

Весь код, парсеры, дашборд, автоматизация и дизайн — вручную, без команды и бюджетов.

---

## ⚙️ Как это работает

```
GitHub / Gitverse / Telegram
            │
            ▼
   GitHub Actions (парсеры)
            │  каждые 2 часа
            ▼
      data/*.json (данные)
            │
            ▼
   docs/index.html (дашборд)
            │
            ▼
      GitHub Pages (сайт)
```

---

## 📁 Структура

```
REMAININGCONNECTIONS/
├── docs/
│   ├── index.html        ← дашборд
│   └── assets/logo.png   ← логотип
├── data/                 ← данные от парсеров
├── scripts/              ← Python-генераторы
└── .github/workflows/    ← автоматизация
```

---

## 🤖 Автоматизация

| Workflow | Что делает | Расписание |
|----------|------------|------------|
| Subscription Discovery | Поиск и проверка подписок | каждые 2 часа |
| TG Proxy Discovery | Поиск и пинг ТГ-прокси | каждый час |
| Utils Discovery | Поиск утилит (Android/iOS/Windows/Linux) | каждые 6 часов |
| Search Query Generator | Автогенерация поисковых запросов | каждые 6 часов |

---

## 🗺️ Планы

- [x] Дашборд на GitHub Pages
- [x] Автопарсеры подписок, прокси, утилит
- [x] Обход блокировок через Google Translate
- [ ] Впихнуть логотип в интерфейс сайта
- [ ] Уведомления в Telegram

---

## 🔗 Ссылки

- 🌐 **Сайт:** [b3b3097.github.io/REMAININGCONNECTIONS](https://b3b3097.github.io/REMAININGCONNECTIONS/)
- 📱 **Telegram:** [@REMAININGCONNECTIONS](https://t.me/REMAININGCONNECTIONS)

---

<div align="center">

**Остаться на связи — это не выбор, это необходимость.**

</div>
```

---

