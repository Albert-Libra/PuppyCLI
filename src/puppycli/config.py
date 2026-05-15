"""Configuration management for PuppyCLI.

Config file defaults to ~/PuppyCLI/config.yaml.
The ``data_dir`` setting can override where sessions, knowledge, and skills are stored.
"""
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG = {
    "api_key": "",
    "model": "deepseek-chat",
    "base_url": "https://api.deepseek.com",
    "theme": "light",
    "python_env": "",
    "data_dir": "",
    "mineru_token": "",
    "max_turns": 50,
}

DEFAULT_CONFIG_DIR = Path.home() / "PuppyCLI"


class Config:
    """Manages PuppyCLI configuration stored as YAML on disk."""

    def __init__(self, config_dir: Path | None = None):
        if config_dir is None:
            config_dir = DEFAULT_CONFIG_DIR
        self._config_dir = Path(config_dir)
        self._config_dir.mkdir(parents=True, exist_ok=True)
        self._file = self._config_dir / "config.yaml"
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Load config from file, falling back to defaults."""
        if self._file.exists():
            with open(self._file, "r", encoding="utf-8") as f:
                loaded = yaml.safe_load(f) or {}
        else:
            loaded = {}
        # Merge loaded over defaults
        self._data = {**DEFAULT_CONFIG, **loaded}

    def _save(self) -> None:
        """Persist current config to disk."""
        with open(self._file, "w", encoding="utf-8") as f:
            yaml.safe_dump(self._data, f, allow_unicode=True, sort_keys=False)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a config value."""
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set a config value and persist."""
        self._data[key] = value
        self._save()

    def __getitem__(self, key: str) -> Any:
        if key not in self._data:
            raise KeyError(key)
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        self.set(key, value)

    def as_dict(self) -> dict[str, Any]:
        """Return a shallow copy of all config."""
        return dict(self._data)

    @property
    def base_dir(self) -> Path:
        """Base directory for all PuppyCLI data (sessions, knowledge, skills).

        Respects the ``data_dir`` config value; falls back to ``~/PuppyCLI``.
        """
        custom = self._data.get("data_dir", "")
        if custom:
            return Path(custom)
        return self._config_dir
