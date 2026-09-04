#!/usr/bin/env python3
"""Advanced proxy monitoring and alerting system for REMAININGCONNECTIONS."""

import json
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

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

    def get_latest_proxy_file(self) -> Optional[Path]:
        """Find the most recent tg_proxies_found.json."""
        try:
            files = list(self.data_dir.glob("tg_proxies_found.json"))
            if not files:
                return None
            return max(files, key=lambda p: p.stat().st_mtime)
        except Exception:
            return None

    def load_proxy_data(self, filepath: Path) -> Optional[List[Dict[str, Any]]]:
        """Load proxies from JSON file."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            proxies = data.get("proxies", [])
            return proxies
        except (json.JSONDecodeError, FileNotFoundError, IOError) as e:
            self.logger.error(f"Failed to load proxies from {filepath}: {e}")
            return None

    def analyze_health(self, proxies: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate comprehensive health metrics."""
        total = len(proxies)
        working = 0
        failed = 0
        latencies = []
        protocols = {}
        
        for p in proxies:
            status = p.get("status", "unknown")
            if status == "working":
                working += 1
                lat = p.get("latency_ms")
                if lat is not None:
                    latencies.append(lat)
                
                proto = p.get("protocol", "unknown")
                protocols[proto] = protocols.get(proto, 0) + 1
            else:
                failed += 1
        
        success_rate = (working / total) if total > 0 else 0.0
        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0
        min_latency = min(latencies) if latencies else 0.0
        max_latency = max(latencies) if latencies else 0.0
        
        return {
            "total_proxies": total,
            "working_count": working,
            "failed_count": failed,
            "success_rate": round(success_rate, 4),
            "avg_latency_ms": round(avg_latency, 2),
            "min_latency_ms": round(min_latency, 2),
            "max_latency_ms": round(max_latency, 2),
            "protocol_distribution": protocols,
            "timestamp": datetime.utcnow().isoformat()
        }

    def check_thresholds(self, metrics: Dict[str, Any]) -> List[str]:
        """Check metrics against thresholds and return alerts."""
        alerts = []
        
        # Success Rate Alert
        if metrics["success_rate"] < THRESHOLD_LOW_SUCCESS_RATE:
            msg = f"CRITICAL: Success rate dropped to {metrics['success_rate']:.2%} (threshold: {THRESHOLD_LOW_SUCCESS_RATE:.2%})"
            alerts.append(msg)
            self.logger.critical(msg)
        
        # Latency Alert
        if metrics["avg_latency_ms"] > THRESHOLD_HIGH_LATENCY_MS:
            msg = f"WARNING: Average latency is high ({metrics['avg_latency_ms']:.0f}ms)"
            alerts.append(msg)
            self.logger.warning(msg)
            
        # Volume Alert (Too few proxies found)
        if metrics["total_proxies"] < 10:
            msg = f"INFO: Very low number of proxies found ({metrics['total_proxies']})"
            alerts.append(msg)
            self.logger.info(msg)
            
        return alerts

    def save_metrics(self, metrics: Dict[str, Any]):
        """Save current metrics to history file."""
        try:
            history = []
            if self.metrics_path.exists():
                try:
                    with open(self.metrics_path, 'r') as f:
                        history = json.load(f)
                except:
                    history = []
            
            history.append(metrics)
            # Keep last 100 entries
            history = history[-100:]
            
            with open(self.metrics_path, 'w') as f:
                json.dump(history, f, indent=2)
                
            self.logger.info(f"Metrics saved to {self.metrics_path}")
        except Exception as e:
            self.logger.error(f"Failed to save metrics: {e}")

    def run_check(self):
        """Main execution loop."""
        self.logger.info("="*50)
        self.logger.info("Starting Proxy Health Check...")
        
        latest_file = self.get_latest_proxy_file()
        if not latest_file:
            self.logger.warning("No proxy data file found.")
            return
            
        self.logger.info(f"Reading data from: {latest_file.name}")
        
        proxies = self.load_proxy_data(latest_file)
        if not proxies:
            self.logger.warning("No proxies loaded.")
            return
            
        metrics = self.analyze_health(proxies)
        alerts = self.check_thresholds(metrics)
        self.save_metrics(metrics)
        
        self.logger.info("-" * 30)
        self.logger.info(f"Summary: {metrics['working_count']} Working / {metrics['failed_count']} Failed")
        self.logger.info(f"Success Rate: {metrics['success_rate']:.2%}")
        self.logger.info(f"Avg Latency: {metrics['avg_latency_ms']:.2f} ms")
        
        if alerts:
            self.logger.warning(f"Generated {len(alerts)} alerts!")
        else:
            self.logger.info("All systems normal.")
            
        self.logger.info("="*50)

def main():
    monitor = ProxyHealthMonitor()
    monitor.run_check()

if __name__ == "__main__":
    main()