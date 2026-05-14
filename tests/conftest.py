"""Shared test fixtures."""
import tempfile
from pathlib import Path

import pytest

from puppycli.config import Config
from puppycli.session.manager import SessionManager


@pytest.fixture
def temp_dir():
    """Create a temporary directory for config/session storage."""
    with tempfile.TemporaryDirectory() as d:
        yield Path(d)


@pytest.fixture
def temp_config(temp_dir):
    """Create a Config pointing at a temp directory."""
    return Config(config_dir=temp_dir)


@pytest.fixture
def temp_manager(temp_dir):
    """Create a SessionManager pointing at a temp directory."""
    return SessionManager(sessions_dir=temp_dir / "sessions")
