#!/usr/bin/env python3
"""Advanced proxy monitoring and alerting system for REMAININGCONNECTIONS."""

import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Any

# Configuration defaults
DEFAULT_DATA_DIR = "data"
ALERT_LOG_PATH = "data/monitoring_alerts.log"
HEALTH_METRICS_PATH = "data/health_metrics.json"

# Thresholds for alerting
THRESHOLD_LOW_SUCCESS_RATE = 0.1  # 10%
THRESHOLD_HIGH_LATENCY_MS = 2000  # 2 seconds
THRESHOLD_CRITICAL_DROP = 0.5     # 50% drop from previous run


class ProxyHealthMonitor:
    """Monitors proxy health metrics and generates alerts."""

    def __init__(self, data_dir: str = DEFAULT_DATA_DIR):
        self.data_dir = Path(data_dir)
        self.alert_log_path = Path(ALERT_LOG_PATH)
        self.metrics_path = Path(HEALTH_METRICS_PATH)
        
        # Setup logging
        self.logger = logging.getLogger("ProxyMonitor")
        self.logger.setLevel(logging.INFO)
        
        # File handler
        fh = logging.FileHandler(str(self.alert_log_path))
        fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(fh)
        
        # Console handler
        ch = logging.StreamHandler()
        ch.setFormatter(logging.Formatter('%(levelname)s: %(message)s'))
        self.logger.addHandler(ch)

    def load_proxy_data(self, filepath: Path) -> list[dict[str, Any]]:
        """Load proxies from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("proxies", [])
        except (OSError, json.JSONDecodeError):
            return []

    def load_subscriptions(self, filepath: Path) -> list[dict[str, Any]]:
        """Load subscriptions from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("subscriptions", [])
        except (OSError, json.JSONDecodeError):
            return []

    def calculate_metrics(self, proxies: list[dict[str, Any]]) -> dict[str, Any]:
        """Calculate health metrics from proxy data."""
        if not proxies:
            return {
                "total": 0,
                "working": 0,
                "success_rate": 0.0,
                "avg_latency_ms": 0.0,
                "protocols": {},
                "bypass_needed": 0,
            }
        
        total = len(proxies)
        working = [p for p in proxies if p.get("status") == "working"]
        working_count = len(working)
        
        # Calculate average latency from working proxies
        latencies = []
        for p in working:
            lat = p.get("tcp_latency_ms") or p.get("latency_ms")
            if lat is not None:
                latencies.append(lat)
        
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        
        # Count protocols
        protocols = {}
        for p in proxies:
            proto = p.get("protocol", "unknown")
            protocols[proto] = protocols.get(proto, 0) + 1
        
        # Count proxies that need bypass
        bypass_needed = len([
            p for p in proxies 
            if p.get("bypass_status") == "works_with_bypass"
        ])
        
        return {
            "total": total,
            "working": working_count,
            "success_rate": working_count / total if total > 0 else 0.0,
            "avg_latency_ms": round(avg_latency, 2),
            "protocols": protocols,
            "bypass_needed": bypass_needed,
        }

    def check_alerts(self, metrics: dict[str, Any], previous_metrics: dict[str, Any] | None) -> list[str]:
        """Check for alert conditions and return alert messages."""
        alerts = []
        
        # Low success rate alert
        if metrics["success_rate"] < THRESHOLD_LOW_SUCCESS_RATE:
            alerts.append(
                f"⚠️ LOW SUCCESS RATE: {metrics['success_rate']:.1%} "
                f"({metrics['working']}/{metrics['total']} working)"
            )
        
        # High latency alert
        if metrics["avg_latency_ms"] > THRESHOLD_HIGH_LATENCY_MS:
            alerts.append(
                f"⚠️ HIGH LATENCY: {metrics['avg_latency_ms']:.0f}ms average"
            )
        
        # Critical drop alert
        if previous_metrics and previous_metrics.get("working", 0) > 0:
            prev_working = previous_metrics["working"]
            curr_working = metrics["working"]
            drop_ratio = (prev_working - curr_working) / prev_working
            
            if drop_ratio > THRESHOLD_CRITICAL_DROP:
                alerts.append(
                    f"🚨 CRITICAL DROP: Working proxies dropped {drop_ratio:.1%} "
                    f"({prev_working} → {curr_working})"
                )
        
        return alerts

    def save_metrics(self, metrics: dict[str, Any]) -> None:
        """Save current metrics to file."""
        metrics["timestamp"] = datetime.utcnow().isoformat() + "Z"
        
        self.metrics_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.metrics_path, 'w', encoding='utf-8') as f:
            json.dump(metrics, f, indent=2, ensure_ascii=False)

    def load_previous_metrics(self) -> dict[str, Any] | None:
        """Load previous metrics if available."""
        if not self.metrics_path.exists():
            return None
        try:
            with open(self.metrics_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (OSError, json.JSONDecodeError):
            return None

    def run_monitoring(self) -> None:
        """Run the monitoring check."""
        self.logger.info("=" * 60)
        self.logger.info("Starting proxy health monitoring")
        
        # Load proxy data
        proxy_file = self.data_dir / "tg_proxies_found.json"
        if not proxy_file.exists():
            self.logger.warning("No proxy data file found")
            return
        
        proxies = self.load_proxy_data(proxy_file)
        if not proxies:
            self.logger.warning("No proxies loaded from data file")
            return
        
        # Calculate current metrics
        metrics = self.calculate_metrics(proxies)
        
        # Load subscription data
        subs_file = self.data_dir / "subscriptions_found.json"
        if subs_file.exists():
            subscriptions = self.load_subscriptions(subs_file)
            working_subs = [s for s in subscriptions if s.get("status") == "working"]
            metrics["subscriptions_total"] = len(subscriptions)
            metrics["subscriptions_working"] = len(working_subs)
        
        # Log current status
        self.logger.info(f"Total proxies: {metrics['total']}")
        self.logger.info(f"Working proxies: {metrics['working']}")
        self.logger.info(f"Success rate: {metrics['success_rate']:.1%}")
        self.logger.info(f"Average latency: {metrics['avg_latency_ms']:.0f}ms")
        self.logger.info(f"Bypass needed: {metrics['bypass_needed']}")
        
        # Check for alerts
        previous_metrics = self.load_previous_metrics()
        alerts = self.check_alerts(metrics, previous_metrics)
        
        if alerts:
            self.logger.warning("ALERTS TRIGGERED:")
            for alert in alerts:
                self.logger.warning(alert)
        else:
            self.logger.info("✅ All metrics within normal range")
        
        # Save metrics
        self.save_metrics(metrics)
        self.logger.info("Metrics saved to " + str(self.metrics_path))
        self.logger.info("=" * 60)


def main() -> None:
    """Main entry point."""
    monitor = ProxyHealthMonitor()
    monitor.run_monitoring()


if __name__ == "__main__":
    main()