"""Configuration management for the HarmonyOS Task List Manager."""

import os
import logging
from pathlib import Path
from typing import Optional
from datetime import timedelta

import yaml

logger = logging.getLogger(__name__)


class Config:
    """Configuration manager."""

    # Default configuration
    DEFAULTS = {
        "data_files": {
            "title_file": "data/title.txt",
            "data_file": "data/tasklist.txt",
        },
        "server": {
            "name": "harmony-tasklist-manager",
            "version": "1.0.0",
            "log_level": "INFO",
        },
        "query": {
            "default_limit": 100,
            "max_limit": 1000,
            "cache_ttl_minutes": 5,
        },
    }

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self._find_config_file()
        self._config = self._load_config()

    @staticmethod
    def _find_config_file() -> str:
        """Find configuration file (by priority)."""
        # 1. Environment variable
        if env_path := os.getenv("HARMONY_TASKLIST_CONFIG"):
            return env_path

        # 2. Current directory
        if Path("config.yaml").exists():
            return "config.yaml"

        # 3. User home directory config
        home_config = Path.home() / ".harmony-tasklist" / "config.yaml"
        if home_config.exists():
            return str(home_config)

        # 4. Return default path (even if it doesn't exist)
        return "config.yaml"

    def _load_config(self) -> dict:
        """Load configuration file."""
        config = self.DEFAULTS.copy()

        config_path = Path(self.config_path)
        if config_path.exists():
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    user_config = yaml.safe_load(f)
                    if user_config:
                        config = self._deep_merge(config, user_config)
            except Exception as e:
                logger.warning(f"Failed to load config file: {e}")

        # Apply environment variable overrides
        self._apply_env_overrides(config)

        return config

    @staticmethod
    def _deep_merge(base: dict, override: dict) -> dict:
        """Deep merge dictionaries."""
        result = base.copy()
        for key, value in override.items():
            if (
                key in result
                and isinstance(result[key], dict)
                and isinstance(value, dict)
            ):
                result[key] = Config._deep_merge(result[key], value)
            else:
                result[key] = value
        return result

    def _apply_env_overrides(self, config: dict):
        """Apply environment variable overrides."""
        # HARMONY_DATA_FILE
        if data_file := os.getenv("HARMONY_DATA_FILE"):
            config["data_files"]["data_file"] = data_file

        # HARMONY_TITLE_FILE
        if title_file := os.getenv("HARMONY_TITLE_FILE"):
            config["data_files"]["title_file"] = title_file

        # HARMONY_LOG_LEVEL
        if log_level := os.getenv("HARMONY_LOG_LEVEL"):
            config["server"]["log_level"] = log_level

    def get(self, *keys):
        """Get configuration value."""
        value = self._config
        for key in keys:
            value = value.get(key)
            if value is None:
                return None
        return value

    @property
    def title_file_path(self) -> str:
        return self.get("data_files", "title_file")

    @property
    def data_file_path(self) -> str:
        return self.get("data_files", "data_file")

    @property
    def default_limit(self) -> int:
        return self.get("query", "default_limit")

    @property
    def max_limit(self) -> int:
        return self.get("query", "max_limit")

    @property
    def cache_ttl(self) -> timedelta:
        minutes = self.get("query", "cache_ttl_minutes")
        return timedelta(minutes=minutes)
