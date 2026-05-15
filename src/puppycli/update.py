"""Update checker for PuppyCLI.

Fetches the latest version from GitHub and compares it with the
locally installed version. Results are cached for 24 hours.
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import NamedTuple

import requests

GITHUB_REPO = "Albert-Libra/PuppyCLI"
GITHUB_RAW = f"https://raw.githubusercontent.com/{GITHUB_REPO}/main"
CACHE_MAX_AGE_SECONDS = 24 * 60 * 60  # 24 hours


class UpdateInfo(NamedTuple):
    update_available: bool
    current_version: str
    latest_version: str


def _parse_semver(version: str) -> tuple[int, ...]:
    """Parse a semver-like version string into a comparable tuple."""
    # Strip leading 'v' if present
    v = version.lstrip("v")
    parts: list[int] = []
    for part in v.split("."):
        # Take only the numeric prefix (handles "-alpha", "-beta", etc.)
        num = ""
        for ch in part:
            if ch.isdigit():
                num += ch
            else:
                break
        if num:
            parts.append(int(num))
        else:
            parts.append(0)
    return tuple(parts)


def _get_cache_path() -> Path:
    """Get the path to the update cache file."""
    config_dir = Path.home() / "PuppyCLI"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / ".update_cache"


def _read_cache() -> tuple[float, str] | None:
    """Read cached (timestamp, latest_version) or None if expired/missing."""
    cache_path = _get_cache_path()
    if not cache_path.exists():
        return None
    try:
        data = json.loads(cache_path.read_text(encoding="utf-8"))
        ts = data.get("timestamp", 0)
        if time.time() - ts < CACHE_MAX_AGE_SECONDS:
            return ts, data.get("latest_version", "")
    except (json.JSONDecodeError, KeyError, OSError):
        pass
    return None


def _write_cache(latest_version: str) -> None:
    """Write the update check result to cache."""
    cache_path = _get_cache_path()
    data = {"timestamp": time.time(), "latest_version": latest_version}
    cache_path.write_text(json.dumps(data), encoding="utf-8")


def get_latest_version() -> str | None:
    """Fetch the latest version string from GitHub's pyproject.toml.

    Returns:
        The version string, or ``None`` if fetching failed.
    """
    try:
        url = f"{GITHUB_RAW}/pyproject.toml"
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        for line in resp.text.splitlines():
            stripped = line.strip()
            if stripped.startswith("version") and "=" in stripped:
                _, _, value = stripped.partition("=")
                value = value.strip().strip('"').strip("'")
                if value:
                    return value
    except (requests.RequestException, OSError):
        pass
    return None


def check_for_update(force: bool = False) -> UpdateInfo:
    """Check whether a newer version of PuppyCLI is available.

    Uses a 24-hour cache to avoid excessive network requests.

    Args:
        force: If ``True``, bypass the cache and always fetch.

    Returns:
        An ``UpdateInfo`` tuple with the comparison result.
    """
    from puppycli import __version__ as current_version

    # Check cache first (unless forced)
    if not force:
        cached = _read_cache()
        if cached is not None:
            _, latest = cached
            if latest:
                try:
                    if _parse_semver(latest) > _parse_semver(current_version):
                        return UpdateInfo(True, current_version, latest)
                    return UpdateInfo(False, current_version, latest)
                except Exception:
                    pass
            return UpdateInfo(False, current_version, "")

    # Fetch latest version
    latest = get_latest_version()
    if latest is None:
        return UpdateInfo(False, current_version, "")

    # Cache the result
    _write_cache(latest)

    try:
        if _parse_semver(latest) > _parse_semver(current_version):
            return UpdateInfo(True, current_version, latest)
    except Exception:
        pass

    return UpdateInfo(False, current_version, latest)
