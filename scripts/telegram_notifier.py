#!/usr/bin/env python3
"""Telegram Notifier for REMAININGCONNECTIONS.

This module handles sending health alerts, summary reports, and 
maintenance notifications directly to a Telegram channel or group.
It integrates with the Proxy Health Monitor to provide real-time feedback.
"""

from __future__ import annotations

import json
import os
import sys
import logging
import requests
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("TelegramNotifier")


class TelegramBotClient:
    """Wrapper for Telegram Bot API."""

    BASE_URL = "https://api.telegram.org/bot"

    def __init__(self, token: str):
        """
        Initialize the client.
        
        Args:
            token: Telegram Bot Token from BotFather.
        """
        if not token:
            raise ValueError("Telegram Bot Token cannot be empty.")
        self.token = token
        self.api_url = f"{self.BASE_URL}{token}"

    def _send_request(self, method: str, data: Optional[Dict] = None, files: Optional[Dict] = None) -> Optional[Any]:
        """
        Send a request to the Telegram API.
        
        Args:
            method: API method name (e.g., sendMessage, sendPhoto).
            data: Dictionary of parameters.
            files: Dictionary of files for multipart uploads.
            
        Returns:
            Parsed JSON response or None on failure.
        """
        url = f"{self.api_url}/{method}"
        try:
            response = requests.post(url, data=data, files=files, timeout=10)
            response.raise_for_status()
            result = response.json()
            if result.get("ok"):
                return result.get("result")
            else:
                logger.error(f"Telegram API Error: {result.get('description')}")
                return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None

    def send_message(self, chat_id: str, text: str, parse_mode: str = "HTML", disable_notification: bool = False) -> bool:
        """
        Send a text message.
        
        Args:
            chat_id: Target chat ID.
            text: Message text.
            parse_mode: Formatting mode (HTML or MarkdownV2).
            
        Returns:
            True if successful, False otherwise.
        """
        data = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": parse_mode,
            "disable_notification": disable_notification
        }
        result = self._send_request("sendMessage", data)
        return result is not None

    def send_photo(self, chat_id: str, photo_path: str, caption: str = "", parse_mode: str = "HTML") -> bool:
        """
        Send a photo with a caption.
        
        Args:
            chat_id: Target chat ID.
            photo_path: Path to the image file.
            caption: Photo caption.
            
        Returns:
            True if successful, False otherwise.
        """
        if not Path(photo_path).exists():
            logger.error(f"Photo file not found: {photo_path}")
            return False
            
        with open(photo_path, 'rb') as photo:
            files = {'photo': photo}
            data = {
                'chat_id': chat_id,
                'caption': caption,
                'parse_mode': parse_mode
            }
        result = self._send_request("sendPhoto", data=data, files=files)
        return result is not None

    def send_document(self, chat_id: str, document_path: str, caption: str = "") -> bool:
        """
        Send a document (e.g., log file, report).
        
        Args:
            chat_id: Target chat ID.
            document_path: Path to the document.
            
        Returns:
            True if successful, False otherwise.
        """
        if not Path(document_path).exists():
            logger.error(f"Document file not found: {document_path}")
            return False
            
        with open(document_path, 'rb') as doc:
            files = {'document': doc}
            data = {
                'chat_id': chat_id,
                'caption': caption
            }
        result = self._send_request("sendDocument", data=data, files=files)
        return result is not None


class AlertFormatter:
    """Formats data into readable Telegram messages."""

    @staticmethod
    def format_health_alert(alert_type: str, metrics: Dict[str, Any]) -> str:
        """Format a health metric alert."""
        msg = f"<b>⚠️ {alert_type} Alert</b>\n\n"
        msg += f"• <b>Total Proxies:</b> {metrics.get('total_proxies', 'N/A')}\n"
        msg += f"• <b>Working:</b> {metrics.get('working_count', 'N/A')}\n"
        msg += f"• <b>Success Rate:</b> {metrics.get('success_rate', 'N/A'):.2%}\n"
        msg += f"• <b>Avg Latency:</b> {metrics.get('avg_latency_ms', 'N/A'):.0f} ms\n"
        msg += f"\n<i>Time: {datetime.utcnow().strftime('%H:%M UTC')}</i>"
        return msg

    @staticmethod
    def format_daily_summary(proxies: List[Dict[str, Any]]) -> str:
        """Generate a daily summary string."""
        total = len(proxies)
        working = sum(1 for p in proxies if p.get("status") == "working")
        rate = (working / total * 100) if total > 0 else 0
        
        protocols = {}
        for p in proxies:
            proto = p.get("protocol", "unknown")
            protocols[proto] = protocols.get(proto, 0) + 1
        
        top_protocols = ", ".join([f"{k}: {v}" for k, v in sorted(protocols.items(), key=lambda x: x[1], reverse=True)[:5]])

        msg = f"<b>📊 Daily Report</b>\n\n"
        msg += f"• <b>Total Found:</b> {total}\n"
        msg += f"• <b>Working:</b> {working} ({rate:.1f}%)\n"
        msg += f"• <b>Top Protocols:</b> {top_protocols}\n"
        msg += f"\n<i>Generated by REMAININGCONNECTIONS</i>"
        return msg


class TelegramNotifier:
    """Main class orchestrating notification logic."""

    def __init__(self, token: str, chat_id: str, data_dir: str = "data"):
        self.client = TelegramBotClient(token)
        self.chat_id = chat_id
        self.formatter = AlertFormatter()
        self.data_dir = Path(data_dir)
        self.alert_log = self.data_dir / "monitoring_alerts.log"

    def notify_on_critical_error(self, error_msg: str):
        """Send immediate alert on critical errors."""
        msg = f"<b>🔴 CRITICAL ERROR</b>\n\n"
        msg += f"{error_msg}\n\n"
        msg += "<i>Please check the logs immediately.</i>"
        self.client.send_message(self.chat_id, msg, disable_notification=True)

    def send_health_update(self, metrics: Dict[str, Any]):
        """Send periodic health update."""
        # Only send if success rate is critically low to avoid spam
        if metrics.get("success_rate", 1.0) < 0.1:
            msg = self.formatter.format_health_alert("LOW SUCCESS RATE", metrics)
            self.client.send_message(self.chat_id, msg)
            logger.info("Sent low success rate alert.")

    def send_daily_report(self):
        """Generate and send the daily summary."""
        # Load latest proxies
        prox_file = self.data_dir / "tg_proxies_found.json"
        if not prox_file.exists():
            logger.warning("No proxy data found for daily report.")
            return

        try:
            with open(prox_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            proxies = data.get("proxies", [])
            
            msg = self.formatter.format_daily_summary(proxies)
            self.client.send_message(self.chat_id, msg)
            logger.info("Daily report sent successfully.")
        except Exception as e:
            logger.error(f"Failed to generate daily report: {e}")
            self.notify_on_critical_error(str(e))

    def send_log_file(self):
        """Send the current monitoring log file."""
        if self.alert_log.exists():
            self.client.send_document(self.chat_id, str(self.alert_log), caption="Latest Monitoring Logs")


def main():
    """CLI entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--token", required=True, help="Telegram Bot Token")
    parser.add_argument("--chat-id", required=True, help="Target Chat ID")
    parser.add_argument("--command", choices=["summary", "log", "test"], required=True, help="Action to perform")
    parser.add_argument("--data-dir", default="data", help="Path to data directory")
    
    args = parser.parse_args()
    
    notifier = TelegramNotifier(args.token, args.chat_id, args.data_dir)
    
    if args.command == "summary":
        notifier.send_daily_report()
    elif args.command == "log":
        notifier.send_log_file()
    elif args.command == "test":
        notifier.client.send_message(args.chat_id, "<b>Test Message</b>\nHello from REMAININGCONNECTIONS!")


if __name__ == "__main__":
    main()