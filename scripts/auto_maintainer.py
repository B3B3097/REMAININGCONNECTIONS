#!/usr/bin/env python3
"""
Auto Maintainer for REMAININGCONNECTIONS.

This module handles automated maintenance tasks for the repository, including:
- Log rotation and cleanup of expired temporary files.
- Compression of historical data files to save storage space.
- Integrity verification of JSON data files.
- Generation of system statistics and health reports.

It ensures the repository remains clean, organized, and efficient 
without manual intervention.
"""

import os
import sys
import json
import gzip
import shutil
import logging
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Tuple

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("AutoMaintainer")


class DataCleaner:
    """Handles cleanup and compression of data files."""

    def __init__(self, data_dir: str = "data", max_age_days: int = 7):
        """
        Initialize the cleaner.
        
        Args:
            data_dir: Path to the data directory.
            max_age_days: Number of days after which logs are considered expired.
        """
        self.data_dir = Path(data_dir)
        self.max_age_days = max_age_days

    def remove_expired_logs(self) -> int:
        """
        Remove log files older than max_age_days.
        
        Returns:
            Number of files removed.
        """
        removed_count = 0
        if not self.data_dir.exists():
            logger.warning(f"Data directory not found: {self.data_dir}")
            return 0

        current_time = datetime.now()

        try:
            for file_path in self.data_dir.glob("*.log"):
                try:
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    age = current_time - mod_time

                    if age > timedelta(days=self.max_age_days):
                        logger.info(f"Removing expired log: {file_path.name} (Age: {age.days} days)")
                        file_path.unlink()
                        removed_count += 1
                except OSError as e:
                    logger.error(f"Error removing {file_path.name}: {e}")
        except Exception as e:
            logger.error(f"Error iterating logs: {e}")

        return removed_count

    def backup_old_json(self) -> int:
        """
        Compress JSON files older than 1 day into .gz backups.
        
        Returns:
            Number of files backed up.
        """
        backed_up_count = 0
        backup_dir = self.data_dir / "backups"
        backup_dir.mkdir(exist_ok=True)

        current_time = datetime.now()

        try:
            for file_path in self.data_dir.glob("*.json"):
                # Skip main active files and backups
                if "found.json" in file_path.name or "merged" in file_path.name:
                    continue
                if file_path.parent == backup_dir:
                    continue

                try:
                    mod_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    age = current_time - mod_time

                    if age > timedelta(days=1):
                        timestamp_str = current_time.strftime("%Y%m%d_%H%M%S")
                        backup_name = f"{file_path.stem}_{timestamp_str}.gz"
                        dest_path = backup_dir / backup_name

                        with open(file_path, 'rb') as f_in:
                            with gzip.open(dest_path, 'wb') as f_out:
                                shutil.copyfileobj(f_in, f_out)
                        
                        logger.info(f"Backed up: {file_path.name} -> {dest_path.name}")
                        backed_up_count += 1
                except Exception as e:
                    logger.error(f"Error backing up {file_path.name}: {e}")
        except Exception as e:
            logger.error(f"Error iterating JSON files: {e}")

        return backed_up_count

    def verify_json_integrity(self) -> Dict[str, Any]:
        """
        Verify integrity of all JSON files in data dir.
        
        Returns:
            Dictionary with summary of valid/invalid files.
        """
        results = {"valid": [], "invalid": []}
        
        try:
            for file_path in self.data_dir.glob("*.json"):
                try:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        json.load(f)
                    results["valid"].append(str(file_path.name))
                except (json.JSONDecodeError, UnicodeDecodeError) as e:
                    results["invalid"].append({"file": str(file_path.name), "error": str(e)})
        except Exception as e:
            logger.error(f"Error during integrity check: {e}")
            
        return results


class StatsCollector:
    """Collects and reports repository statistics."""

    def __init__(self, root_dir: str = "."):
        self.root_dir = Path(root_dir)

    def collect(self) -> Dict[str, Any]:
        """
        Collect various statistics about the repository.
        
        Returns:
            Dictionary containing stats.
        """
        stats = {
            "total_files": 0,
            "total_lines_of_code": 0,
            "total_size_bytes": 0,
            "python_files": 0,
            "js_files": 0,
            "json_files": 0,
            "yml_files": 0,
            "last_modified": None
        }

        for item in self.root_dir.rglob("*"):
            if item.is_file():
                stats["total_files"] += 1
                stats["total_size_bytes"] += item.stat().st_size

                suffix = item.suffix.lower()
                if suffix == '.py':
                    stats["python_files"] += 1
                    try:
                        with open(item, 'r', encoding='utf-8', errors='ignore') as f:
                            stats["total_lines_of_code"] += sum(1 for _ in f)
                    except Exception:
                        pass
                elif suffix == '.js':
                    stats["js_files"] += 1
                elif suffix == '.json':
                    stats["json_files"] += 1
                elif suffix == '.yml' or suffix == '.yaml':
                    stats["yml_files"] += 1

        return stats

    def print_report(self, stats: Dict[str, Any]):
        """Print formatted statistics report."""
        print("\n" + "="*60)
        print("REMAININGCONNECTIONS SYSTEM STATISTICS")
        print("="*60)
        print(f"{'Total Files':<25} : {stats['total_files']}")
        print(f"{'Python Scripts':<25} : {stats['python_files']}")
        print(f"{'JS Files':<25} : {stats['js_files']}")
        print(f"{'JSON Data Files':<25} : {stats['json_files']}")
        print(f"{'Total Lines of Code':<25} : {stats['total_lines_of_code']:,}")
        print(f"{'Total Size':<25} : {stats['total_size_bytes'] / (1024*1024):.2f} MB")
        print("="*60 + "\n")


class AutoMaintainer:
    """Main orchestrator for maintenance tasks."""

    def __init__(self, data_dir: str = "data", dry_run: bool = False):
        self.cleaner = DataCleaner(data_dir=data_dir)
        self.stats = StatsCollector()
        self.dry_run = dry_run

    def run(self):
        """Execute the full maintenance routine."""
        logger.info("Starting Maintenance Routine...")
        
        if not self.dry_run:
            # 1. Cleanup Logs
            logs_removed = self.cleaner.remove_expired_logs()
            logger.info(f"Removed {logs_removed} expired log files.")

            # 2. Backup Old Data
            backups_created = self.cleaner.backup_old_json()
            logger.info(f"Created {backups_created} backups of old data.")

            # 3. Verify Integrity
            integrity = self.cleaner.verify_json_integrity()
            if integrity["invalid"]:
                logger.warning(f"Found {len(integrity['invalid'])} invalid JSON files!")
                for inv in integrity["invalid"]:
                    logger.warning(f"  Invalid: {inv['file']} - {inv['error']}")
            else:
                logger.info("All JSON files verified successfully.")
        else:
            logger.info("[DRY RUN] Skipping file modifications.")
            integrity = {"valid": [], "invalid": []}

        # 4. Generate Report
        stats = self.stats.collect()
        self.stats.print_report(stats)
        
        logger.info("Maintenance routine completed.")


def main():
    """CLI Entry point."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without modifying files")
    parser.add_argument("--data-dir", default="data", help="Path to the data directory")
    
    args = parser.parse_args()
    
    maintainer = AutoMaintainer(data_dir=args.data_dir, dry_run=args.dry_run)
    maintainer.run()


if __name__ == "__main__":
    main()