# 🛜 REMAININGCONNECTIONS · Остаться на связи

Дашборд мониторинга подписок, ТГ-прокси и Open Source утилит.

---

## 🌐 Ссылки

- **Сайт:** https://b3b3097.github.io/REMAININGCONNECTIONS/
- **Обход блокировок:** [Google Translate](https://translate.google.com/translate?sl=en&tl=ru&u=https://b3b3097.github.io/REMAININGCONNECTIONS/)
- **Telegram:** [@REMAININGCONNECTIONS](https://t.me/REMAININGCONNECTIONS)

---

## 📦 Что внутри

| Компонент | Описание |
|-----------|----------|
| `docs/index.html` | Главный дашборд с вкладками |
| `.github/workflows/` | GitHub Actions для парсинга |
| `scripts/` | Python-генераторы данных |
| `data/` | Автоматически генерируемые JSON |

---

## 🚀 Как работает

1. **GitHub Actions** запускаются по расписанию
2. Парсеры собирают данные с GitHub/Gitverse
3. Результаты сохраняются в `data/*.json`
4. Сайт автоматически деплоится на GitHub Pages

---

## ⚙️ Workflow

| Название | Что делает |
|----------|------------|
| `subscription-discovery.yml` | Поиск и проверка подписок |
| `tg-proxy-discovery.yml` | Поиск ТГ-прокси |
| `utils-discovery.yml` | Поиск Open Source утилит |
| `search-query-generator.yml` | Генерация поисковых запросов |
| `deploy-pages.yml` | Деплой сайта |

---

_Автоматически обновляется каждые несколько часов._