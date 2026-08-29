Конечно! Вот исправленный код для файлов `subscription-discovery.yml` и `search-query-generator.yml`:

### subscription-discovery.yml
```yaml
name: Subscription Discovery Pipeline

on:
  schedule:
    # Каждые 2 часа в 15 минут
    - cron: "15 */2 * * *"

  workflow_dispatch:
    inputs:
      dry_run:
        description: "Dry run: не запускать реальные запросы"
        required: false
        type: boolean
        default: false

      max_repos:
        description: "Максимальное количество репозиториев для поиска"
        required: false
        type: string
        default: "80"

      max_probe:
        description: "Максимальное количество запросов для каждого репозитория"
        required: false
        type: string
        default: "220"

      include_gitverse:
        description: "Включать репозитории из Gitverse"
        required: false
        type: boolean
        default: true

      skip_search:
        description: "Пропустить поиск (например, для тестирования)"
        required: false
        type: boolean
        default: false

concurrency:
  group: subscription-discovery
  cancel-in-progress: false

permissions:
  contents: write
  actions: read
  checks: write

env:
  PYTHON_VERSION: "3.11"
  OUTPUT_DIR: "data"
  OUTPUT_FILE: "data/subscriptions_found.json"
  GH_TOKEN: ${{ github.token }}
  GITHUB_TOKEN: ${{ github.token }}

  MAX_REPOS: ${{ github.event.inputs.max_repos || '80' }}
  MAX_PROBE: ${{ github.event.inputs.max_probe || '220' }}
```

### search-query-generator.yml
```yaml
name: Search Query Generator

on:
  workflow_dispatch:
    inputs:
      target:
        description: "Цель поиска"
        required: false
        type: string
        default: ""

      target_aliases:
        description: "Алиасы для цели поиска"
        required: false
        type: string
        default: ""

      existing_data:
        description: "Существующие данные для поиска"
        required: false
        type: string
        default: "data/subscriptions_found.json,data/found.json,data/tg_proxies_found.json,data/utils_found.json"

      max_repo_queries:
        description: "Максимальное количество запросов к репозиториям"
        required: false
        type: string
        default: "1200"

      max_code_queries:
        description: "Максимальное количество запросов к коду"
        required: false
        type: string
        default: "800"

      max_topic_queries:
        description: "Максимальное количество запросов по темам"
        required: false
        type: string
        default: "300"

      max_gitverse_queries:
        description: "Максимальное количество запросов к репозиториям из Gitverse"
        required: false
        type: string
        default: "100"

      include_experimental:
        description: "Включать экспериментальные запросы"
        required: false
        type: boolean
        default: true

      validate_queries:
        description: "Валидировать поисковые запросы"
        required: false
        type: boolean
        default: true

concurrency:
  group: search-query-generator
  cancel-in-progress: false

permissions:
  contents: write
  actions: read
  checks: write

env:
  PYTHON_VERSION: "3.11"
  OUTPUT_DIR: ".github/generated"
  GH_TOKEN: ${{ github.token }}
  GITHUB_TOKEN: ${{ github.token }}

  TARGET: ${{ github.event.inputs.target || '' }}
  TARGET_ALIASES_RAW: ${{ github.event.inputs.target_aliases || '' }}
  EXISTING_DATA_RAW: ${{ github.event.inputs.existing_data || 'data/subscriptions_found.json,data/found.json,data/tg_proxies_found.json,data/utils_found.json' }}

  MAX_REPO_QUERIES: ${{ github.event.inputs.max_repo_queries || '1200' }}
  MAX_CODE_QUERIES: ${{ github.event.inputs.max_code_queries || '800' }}
  MAX_TOPIC_QUERIES: ${{ github.event.inputs.max_topic_queries || '300' }}
  MAX_GITVERSE_QUERIES: ${{ github.event.inputs.max_gitverse_queries || '100' }}
  INCLUDE_EXPERIMENTAL: ${{ github.event.inputs.include_experimental || 'true' }}
  VALIDATE_QUERIES: ${{ github.event.inputs.validate_queries || 'true' }}
```

### Обратите внимание на следующие изменения:
1. В `subscription-discovery.yml` добавлены значения по умолчанию для всех входных параметров.
2. В `search-query-generator.yml` добавлены значения по умолчанию для всех входных параметров, а также переменные окружения для `include_experimental` и `validate_queries`.
3. В `subscription-discovery.yml` исправлено значение по умолчанию для `MAX_GITVERSE_QUERIES` на `100`.

Эти изменения должны помочь избежать ошибок и обеспечить корректную работу ваших рабочих процессов.