"""Tests for config module."""
from pathlib import Path

from puppycli.config import Config


def test_config_defaults(temp_config: Config):
    """New config should have sensible defaults."""
    assert temp_config.get("model") == "deepseek-chat"
    assert temp_config.get("base_url") == "https://api.deepseek.com"
    assert temp_config.get("api_key") == ""
    assert temp_config.get("theme") == "light"


def test_config_get_set(temp_config: Config):
    """Set and get config values."""
    temp_config.set("api_key", "sk-test123")
    assert temp_config.get("api_key") == "sk-test123"


def test_config_persistence(temp_dir: Path):
    """Config should persist to disk and reload."""
    config1 = Config(config_dir=temp_dir)
    config1.set("api_key", "sk-persist-test")

    config2 = Config(config_dir=temp_dir)
    assert config2.get("api_key") == "sk-persist-test"


def test_config_setitem_getitem(temp_config: Config):
    """Dict-style access should work."""
    temp_config["model"] = "deepseek-v4"
    assert temp_config["model"] == "deepseek-v4"
