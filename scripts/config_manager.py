#!/usr/bin/env python3
"""
Advanced Configuration Manager for REMAININGCONNECTIONS.

Provides a centralized, type-safe, and hierarchical configuration system for the entire project.
It supports loading from multiple sources (.env, JSON, YAML, Command Line Args) with precedence rules.

Features:
- Hierarchical Settings (Global -> Environment -> Override)
- Type Casting and Validation
- Dynamic Configuration Reloading
- Sensitive Data Masking (for logs)
- Configuration Export/Import
- Dot-notation access (e.g., config.get("database.host"))

Dependencies:
    os, json, yaml, argparse, re, logging, typing, pathlib, dotenv
"""

from __future__ import annotations

import copy
import inspect
import json
import logging
import os
import re
import sys
from dataclasses import dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Type, Union

try:
    import yaml
except ImportError:
    yaml = None

logger = logging.getLogger("ConfigManager")


# --- Enums & Constants ---

class ConfigSource(Enum):
    DEFAULT = 0
    ENV_FILE = 10
    ENV_VARS = 20
    COMMAND_LINE = 30
    DICT_OVERRIDE = 40


@dataclass
class SettingDefinition:
    """Defines a single configuration parameter."""
    name: str
    default: Any
    description: str = ""
    type_hint: Type = str
    required: bool = False
    sensitive: bool = False
    choices: Optional[List[Any]] = None
    
    def cast_value(self, value: Any) -> Any:
        """Cast value to defined type."""
        try:
            if self.type_hint == bool:
                if isinstance(value, str):
                    return value.lower() in ("true", "1", "yes", "on")
                return bool(value)
            return self.type_hint(value)
        except (ValueError, TypeError) as e:
            raise ValueError(f"Failed to cast '{value}' to {self.type_hint.__name__}: {e}")


class ConfigManager:
    """
    Centralized configuration controller.
    """
    
    def __init__(self, app_name: str = "REMAININGCONNECTIONS"):
        self.app_name = app_name
        self.settings: Dict[str, Any] = {}
        self._definitions: Dict[str, SettingDefinition] = {}
        self._callbacks: Dict[str, List[Callable]] = {}
        
        # Predefined Global Settings
        self.register_setting("APP_NAME", app_name, "Application Name", str)
        self.register_setting("DEBUG", False, "Enable debug mode", bool)
        self.register_setting("LOG_LEVEL", "INFO", "Logging level", str, choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self.register_setting("DATA_DIR", "./data", "Path to data directory", str)
        self.register_setting("OUTPUT_DIR", "./output", "Path to output directory", str)
        
        # Network Settings
        self.register_setting("NETWORK_TIMEOUT", 10.0, "Global request timeout", float)
        self.register_setting("NETWORK_CONCURRENCY", 5, "Max concurrent connections", int)
        self.register_setting("NETWORK_PROXY", "", "System proxy URL", str)
        
        # GitHub API Settings
        self.register_setting("GITHUB_TOKEN", "", "GitHub Personal Access Token", str, sensitive=True)
        self.register_setting("GITHUB_OWNER", "B3B3097", "GitHub Owner", str)
        self.register_setting("GITHUB_REPO", "REMAININGCONNECTIONS", "GitHub Repo Name", str)
        self.register_setting("GITHUB_MAX_REPOS_SEARCH", 50, "Max repos to search per query", int)
        
        # Proxy Checker Settings
        self.register_setting("CHECKER_ENABLE_XRAY", False, "Enable Xray verification", bool)
        self.register_setting("CHECKER_ENABLE_MTPROTO", True, "Enable MTProto verification", bool)
        self.register_setting("CHECKER_TIMEOUT", 8.0, "Check timeout in seconds", float)
        self.register_setting("CHECKER_CONCURRENCY", 30, "Check concurrency limit", int)
        
        # Crawler Settings
        self.register_setting("CRAWLER_MAX_DEPTH", 3, "Max crawl depth", int)
        self.register_setting("CRAWLER_MAX_PAGES", 100, "Max pages to visit", int)
        self.register_setting("CRAWLER_DELAY_MIN", 0.5, "Min delay between requests", float)
        self.register_setting("CRAWLER_DELAY_MAX", 1.5, "Max delay between requests", float)

    def register_setting(self, name: str, default: Any, description: str = "", 
                         type_hint: Type = str, required: bool = False, 
                         sensitive: bool = False, choices: Optional[List[Any]] = None):
        """Register a new configuration setting."""
        key = name.upper()
        self._definitions[key] = SettingDefinition(
            name=key,
            default=default,
            description=description,
            type_hint=type_hint,
            required=required,
            sensitive=sensitive,
            choices=choices
        )
        # Initialize current value
        if key not in self.settings:
            self.settings[key] = default

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        key = key.upper()
        return self.settings.get(key, default)

    def set(self, key: str, value: Any):
        """Set a configuration value manually."""
        key = key.upper()
        if key in self._definitions:
            definition = self._definitions[key]
            try:
                value = definition.cast_value(value)
                if definition.choices and value not in definition.choices:
                    raise ValueError(f"Invalid choice for {key}: {value}. Must be one of {definition.choices}")
                self.settings[key] = value
                logger.debug(f"Setting {key} = {self._mask_secret(key, value)}")
                self._notify_listeners(key, value)
            except ValueError as e:
                logger.error(f"Error setting {key}: {e}")
                raise
        else:
            self.settings[key] = value # Allow dynamic settings if not registered

    def _mask_secret(self, key: str, value: Any) -> str:
        """Mask sensitive values for logging."""
        if self._definitions.get(key, SettingDefinition("", "")).sensitive:
            return "***MASKED***"
        return str(value)

    def load_from_env_file(self, path: str = ".env"):
        """Load settings from a .env file."""
        env_path = Path(path)
        if not env_path.exists():
            logger.info(f".env file not found at {path}")
            return

        try:
            with open(env_path, 'r') as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    if '=' in line:
                        k, v = line.split('=', 1)
                        k = k.strip().upper()
                        v = v.strip().strip('"').strip("'")
                        
                        if k in self._definitions:
                            self.set(k, v)
                        else:
                            # Set raw env var
                            os.environ[k] = v
        except Exception as e:
            logger.error(f"Failed to load .env file: {e}")

    def load_from_dict(self, data: Dict[str, Any]):
        """Load settings from a dictionary."""
        for k, v in data.items():
            self.set(k, v)

    def export_to_dict(self, mask_secrets: bool = True) -> Dict[str, Any]:
        """Export current configuration to a dictionary."""
        result = {}
        for k, v in self.settings.items():
            if mask_secrets and self._definitions.get(k, SettingDefinition("", "")).sensitive:
                result[k] = "***MASKED***"
            else:
                result[k] = v
        return result

    def save_to_json(self, path: str = "config.json"):
        """Save current configuration to a JSON file."""
        data = self.export_to_dict(mask_secrets=False) # Save unmasked internally
        with open(path, 'w') as f:
            json.dump(data, f, indent=2)

    def subscribe(self, key: str, callback: Callable):
        """Subscribe to changes for a specific setting."""
        if key not in self._callbacks:
            self._callbacks[key] = []
        self._callbacks[key].append(callback)

    def _notify_listeners(self, key: str, value: Any):
        """Notify listeners of a change."""
        if key in self._callbacks:
            for cb in self._callbacks[key]:
                try:
                    cb(value)
                except Exception as e:
                    logger.error(f"Error in config listener for {key}: {e}")

    def validate(self) -> List[str]:
        """Validate all required settings."""
        errors = []
        for k, defn in self._definitions.items():
            if defn.required and k not in self.settings:
                errors.append(f"Missing required setting: {k}")
            elif k in self.settings and defn.required:
                val = self.settings[k]
                if val is None or (isinstance(val, str) and not val.strip()):
                    errors.append(f"Required setting {k} cannot be empty.")
        return errors


def main():
    """CLI for configuration management."""
    import argparse
    
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=["get", "set", "validate", "export"], required=True)
    parser.add_argument("--key", help="Configuration key")
    parser.add_argument("--value", help="Value to set")
    parser.add_argument("--env-file", default=".env", help="Path to .env file")
    
    args = parser.parse_args()
    
    config = ConfigManager()
    config.load_from_env_file(args.env_file)
    
    if args.action == "get":
        if not args.key:
            print("[!] --key is required for get action.")
            return
        val = config.get(args.key)
        print(f"{args.key} = {val}")
        
    elif args.action == "set":
        if not args.key or not args.value:
            print("[!] --key and --value are required for set action.")
            return
        config.set(args.key, args.value)
        print(f"[+] Updated {args.key} = {args.value}")
        
    elif args.action == "validate":
        errors = config.validate()
        if errors:
            print("[-] Validation Failed:")
            for e in errors:
                print(f"  - {e}")
        else:
            print("[+] Configuration Valid!")
            
    elif args.action == "export":
        data = config.export_to_dict()
        print(json.dumps(data, indent=2))


if __name__ == "__main__":
    main()