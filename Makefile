# Makefile for REMAININGCONNECTIONS Project
# Usage: make <target>
# Example: make install, make monitor, make generate-dashboard

.PHONY: all install monitor validate-deep generate-dashboard clean help

# Default python interpreter. Override with PYTHON=python3 if needed.
PYTHON ?= python3

# Default target
all: help

help:
	@echo "REMAININGCONNECTIONS - Makefile"
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'
	@echo ""

install: ## Install all project dependencies
	@echo "Installing dependencies..."
	pip install --upgrade pip
	pip install -r requirements.txt
	@echo "Done."

monitor: ## Run the health monitor manually
	@echo "Starting Proxy Health Monitor..."
	$(PYTHON) scripts/proxy_monitoring_alerts.py

validate-deep: ## Run deep validation on proxy data
	@echo "Starting Deep Proxy Validation..."
	$(PYTHON) scripts/batch_validator.py --input data/tg_proxies_found.json --output data/deep_checked.json
	@echo "Deep validation complete. Output: data/deep_checked.json"

generate-dashboard: ## Generate the static dashboard HTML
	@echo "Generating Dashboard..."
	$(PYTHON) scripts/dashboard_generator.py
	@echo "Dashboard generated in docs/index.html"

clean: ## Clean up temporary files and caches
	@echo "Cleaning up..."
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage
	@echo "Cleanup complete."