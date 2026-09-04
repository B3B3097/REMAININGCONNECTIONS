monitor: ## Run the health monitor manually
	$(PYTHON) scripts/proxy_monitoring_alerts.py

validate-deep: ## Run deep validation on proxy data
	$(PYTHON) scripts/batch_validator.py --input data/tg_proxies_found.json --output data/deep_checked.json