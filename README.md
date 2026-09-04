# 🌐 REMAININGCONNECTIONS

> **Автоматизированный комплекс для поиска, валидации и мониторинга прокси-соединений.**

Проект предназначен для глубокого анализа сетевой инфраструктуры, обнаружения активных узлов (VLESS, VMess, Trojan, Shadowsocks) и оценки их производительности. Система полностью автоматизирована, использует современные методы TLS-fingerprinting и предоставляет интерактивную панель управления.

---

## 🔗 Официальные ресурсы

<p align="center">
  <a href="https://t.me/YOUR_CHANNEL_NAME_HERE" target="_blank">
    <img src="https://img.shields.io/badge/Telegram-%40Channel-blue?style=for-the-badge&logo=telegram" alt="Telegram"/>
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

*   **Deep Validation Engine**: Проверка прокси на уровне TLS-рукопожатий и анализ отпечатков браузера.
*   **Real-time Analytics**: Динамическое обновление статистики доступности и скорости.
*   **Automated CI/CD**: Независимый сбор данных и деплой отчетов через GitHub Actions.
*   **Proxy Rotation**: Интеллектуальное распределение нагрузки между узлами.
*   **Docker Ready**: Поддержка контейнеризации для развертывания в любой среде.

---

## 🛠 Технический стек

*   **Backend**: Python 3.11+ (Asyncio, AIOHTTP)
*   **Validation**: Xray-core, Custom TCP/TLS Simulators
*   **Frontend**: TailwindCSS, Chart.js (Static Generation)
*   **DevOps**: GitHub Actions, Docker, Makefile

---

## 🚀 Быстрый старт

```bash
# Клонировать репозиторий
git clone https://github.com/B3B3097/REMAININGCONNECTIONS.git
cd REMAININGCONNECTIONS

# Установить зависимости
make install

# Запустить локальный сервер статистики
make run-api

# Сгенерировать HTML дашборд
make generate-dashboard
```

---

## 📝 Последние обновления

### ✨ Новые функции
- ⚡ **Faster updates**: Все воркфлоу теперь работают **каждый час**.
- 🛡️ **MTProto Validation**: Полная поддержка проверки MTProto.
- 📈 **Health Monitoring**: Мониторинг метрик каждые 30 минут.
- 🎨 **New Interface**: Обновленный красивый интерфейс дашборда.

### 🛠️ Advanced Capabilities
Это репозиторий включает надежный конвейер обработки данных:

1.  **Xray Manager**: Автоматическая установка и настройка Xray-core.
2.  **Data Processor**: 
    -   **Cleaner**: Валидация URL и удаление мусора.
    -   **Fuzzy Matcher**: Поиск почти идентичных прокси.
    -   **Scorer**: Ранжирование по задержке и статусу.
3.  **Config Importer**: Импорт конфигураций Clash, V2Ray, Surge.
4.  **Auto Maintainer**: Ротация логов и сжатие данных.
5.  **Docker Support**: Файлы `Dockerfile` и `docker-compose.yml`.
6.  **CI/CD Automation**: Программное управление действиями GitHub.
7.  **Local API Server**: Асинхронный сервер (`api_server.py`).
8.  **Deep Validation**: Симуляция TLS (`advanced_validator.py`).
9.  **Dashboard Generator**: Генерация статической страницы (`dashboard_generator.py`).
10. **Batch Validator**: Пакетная обработка (`batch_validator.py`).

---

## About the project

Данный проект является инструментом для исследования сетей и тестирования соединений. Использование предоставленного кода осуществляется на ваш собственный риск.