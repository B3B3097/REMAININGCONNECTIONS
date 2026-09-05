 # Makefile for REMAININGCONNECTIONS Project
# Usage: make <target>
# Example: make install, make extract, make all

.PHONY: all install test clean extract validate export health summary help
.PHONY: monitor validate-deep generate-dashboard
.PHONY: extract-tg extract-http validate-tg validate-http validate-socks
.PHONY: quick watch stats view-tg view-http view-socks setup-dirs check-env

# Default python interpreter. Override with PYTHON=python3 if needed.
PYTHON ?= python3
PIP := $(PYTHON) -m pip

# Colors for output
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
CYAN := \033[0;36m
NC := \033[0m # No Color

# Default target
all: help

help: ## Show this help message
	@echo "$(CYAN)REMAININGCONNECTIONS - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

install: ## Install all project dependencies
	@echo "$(GREEN)Installing dependencies...$(NC)"
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements.txt
	@echo "$(GREEN)✓ Dependencies installed$(NC)"

test: ## Run system integration tests
	@echo "$(GREEN)Running system tests...$(NC)"
	$(PYTHON) scripts/test_system.py

clean: ## Clean up temporary files and caches
	@echo "$(YELLOW)Cleaning up...$(NC)"
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf extracted/*.json
	rm -rf checked/*.json
	rm -rf exports/*
	rm -f exports.zip
	@echo "$(GREEN)✓ Cleanup complete$(NC)"

setup-dirs: ## Create required directories
	@echo "$(GREEN)Creating directories...$(NC)"
	@mkdir -p data extracted checked exports .github/workflows .github/badges
	@touch data/.gitkeep extracted/.gitkeep checked/.gitkeep
	@echo "$(GREEN)✓ Directories created$(NC)"

extract-tg: ## Extract Telegram proxies from GitHub
	@echo "$(GREEN)Extracting Telegram proxies...$(NC)"
	$(PYTHON) scripts/extract_tg_proxies.py

extract-http: ## Extract HTTP/SOCKS proxies from GitHub
	@echo "$(GREEN)Extracting HTTP/SOCKS proxies...$(NC)"
	$(PYTHON) scripts/extract_http_socks_proxies.py

extract: extract-tg extract-http ## Extract all proxies from GitHub

validate-tg: ## Validate Telegram proxies
	@echo "$(GREEN)Validating Telegram proxies...$(NC)"
	$(PYTHON) scripts/check_tg_proxies.py \
		--input extracted/tg_proxies_extracted.json \
		--output data/tg_proxies_found.json \
		--concurrency 30

validate-http: ## Validate HTTP proxies
	@echo "$(GREEN)Validating HTTP proxies...$(NC)"
	$(PYTHON) scripts/validate_http_socks_proxies.py \
		--input extracted/http_proxies_extracted.json \
		--output data/http_proxies_found.json \
		--protocols http https \
		--concurrency 50

validate-socks: ## Validate SOCKS proxies
	@echo "$(GREEN)Validating SOCKS proxies...$(NC)"
	$(PYTHON) scripts/validate_http_socks_proxies.py \
		--input extracted/socks_proxies_extracted.json \
		--output data/socks_proxies_found.json \
		--protocols socks4 socks5 \
		--concurrency 50

validate: validate-tg validate-http validate-socks ## Validate all proxies

validate-deep: ## Run deep validation on proxy data
	@echo "$(GREEN)Starting Deep Proxy Validation...$(NC)"
	$(PYTHON) scripts/batch_validator.py --input data/tg_proxies_found.json --output data/deep_checked.json
	@echo "$(GREEN)✓ Deep validation complete. Output: data/deep_checked.json$(NC)"

summary: ## Generate summary report
	@echo "$(GREEN)Generating summary...$(NC)"
	$(PYTHON) scripts/generate_summary.py

export: ## Export proxies to multiple formats
	@echo "$(GREEN)Exporting proxies...$(NC)"
	$(PYTHON) scripts/export_formats.py

health: ## Run health check
	@echo "$(GREEN)Running health check...$(NC)"
	$(PYTHON) scripts/health_check.py

monitor: ## Run the health monitor manually
	@echo "$(GREEN)Starting Proxy Health Monitor...$(NC)"
	$(PYTHON) scripts/proxy_monitoring_alerts.py

generate-dashboard: ## Generate the static dashboard HTML
	@echo "$(GREEN)Generating Dashboard...$(NC)"
	$(PYTHON) scripts/dashboard_generator.py
	@echo "$(GREEN)✓ Dashboard generated in docs/index.html$(NC)"

pipeline: extract validate summary export health ## Run complete pipeline
	@echo "$(GREEN)✓ Complete pipeline finished$(NC)"

quick: ## Quick extract and validate (limited proxies)
	@echo "$(GREEN)Running quick pipeline...$(NC)"
	MAX_EXTRACT_PROXIES=100 MAX_CHECK_PROXIES=50 $(PYTHON) scripts/extract_tg_proxies.py
	$(PYTHON) scripts/check_tg_proxies.py \
		--input extracted/tg_proxies_extracted.json \
		--output data/tg_proxies_found.json \
		--max-check 50 \
		--concurrency 20
	$(PYTHON) scripts/generate_summary.py
	@echo "$(GREEN)✓ Quick pipeline finished$(NC)"

watch: ## Watch data files for changes (requires jq)
	@echo "$(YELLOW)Watching data files (Ctrl+C to stop)...$(NC)"
	@while true; do \
		clear; \
		echo "$(GREEN)REMAININGCONNECTIONS - Live Data$(NC)"; \
		echo ""; \
		if [ -f data/summary.json ]; then \
			jq -r '"Total: \(.total_proxies) | Subscriptions: \(.categories.subscriptions.count) | Telegram: \(.categories.telegram.count) | HTTP: \(.categories.http.count) | SOCKS: \(.categories.socks.count)"' data/summary.json; \
		else \
			echo "$(RED)No summary data available$(NC)"; \
		fi; \
		echo ""; \
		echo "$(YELLOW)Updated: $$(date)$(NC)"; \
		sleep 5; \
	done

stats: ## Show current statistics
	@echo "$(GREEN)Current Statistics$(NC)"
	@echo ""
	@if [ -f data/summary.json ]; then \
		echo "Total Proxies: $$(jq -r '.total_proxies' data/summary.json)"; \
		echo ""; \
		echo "By Category:"; \
		jq -r '.categories | to_entries[] | "  \(.key): \(.value.count)"' data/summary.json; \
	else \
		echo "$(RED)No summary data available$(NC)"; \
	fi

view-tg: ## View Telegram proxies (requires jq and less)
	@if [ -f data/tg_proxies_found.json ]; then \
		jq '.' data/tg_proxies_found.json | less; \
	else \
		echo "$(RED)No Telegram proxy data available$(NC)"; \
	fi

view-http: ## View HTTP proxies (requires jq and less)
	@if [ -f data/http_proxies_found.json ]; then \
		jq '.' data/http_proxies_found.json | less; \
	else \
		echo "$(RED)No HTTP proxy data available$(NC)"; \
	fi

view-socks: ## View SOCKS proxies (requires jq and less)
	@if [ -f data/socks_proxies_found.json ]; then \
		jq '.' data/socks_proxies_found.json | less; \
	else \
		echo "$(RED)No SOCKS proxy data available$(NC)"; \
	fi

check-env: ## Check environment and dependencies
	@echo "$(GREEN)Environment Check$(NC)"
	@echo ""
	@echo "Python version: $$($(PYTHON) --version)"
	@echo "Pip version: $$($(PIP) --version | cut -d' ' -f2)"
	@echo ""
	@echo "Required packages:"
	@$(PIP) list | grep -E "(PyYAML|requests|aiohttp|pytest|rich|tabulate)" || echo "$(RED)Some packages missing - run 'make install'$(NC)"
	@echo ""
	@echo "Git status:"
	@git status --short || echo "$(RED)Not a git repository$(NC)"