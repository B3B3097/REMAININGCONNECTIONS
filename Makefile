# Makefile for REMAININGCONNECTIONS
# Automates common development tasks

PYTHON ?= python3
PIP ?= pip3
VENV ?= .venv

.PHONY: help install test lint clean dashboard server docker

help: ## Display this help message
	@echo "Usage:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	$(PYTHON) -m venv $(VENV)
	$(VENV)/bin/pip install --upgrade pip
	$(VENV)/bin/pip install -r requirements.txt
	@echo "[+] Dependencies installed in $(VENV)"

shell: ## Activate virtual environment
	@echo "Activating virtual environment..."
	source $(VENV)/bin/activate

test: ## Run tests
	$(VENV)/bin/pytest tests/ -v --tb=short

lint: ## Run linter (flake8/ruff if available)
	$(VENV)/bin/python -m flake8 scripts/ --max-line-length=120 --ignore=E501,W503 || echo "Flake8 not found, skipping."

clean: ## Clean up generated files and caches
	rm -rf .pytest_cache
	rm -rf __pycache__
	rm -f coverage.xml
	find . -type f -name "*.pyc" -delete
	rm -rf $(VENV)
	@echo "[+] Cleanup complete."

generate-dashboard: ## Generate the static dashboard locally
	$(PYTHON) scripts/dashboard_generator.py

run-api: ## Start the local API server
	$(PYTHON) scripts/api_server.py

synthetic-test: ## Run a full pipeline test with synthetic data
	@echo "[*] Generating synthetic data..."
	$(PYTHON) scripts/synthetic_data_generator.py
	@echo "[*] Processing data..."
	$(PYTHON) scripts/data_processor.py
	@echo "[*] Generating dashboard..."
	$(PYTHON) scripts/dashboard_generator.py
	@echo "[+] Full pipeline test finished."

monitor: ## Run the health monitor manually
	$(PYTHON) scripts/proxy_monitoring_alerts.py