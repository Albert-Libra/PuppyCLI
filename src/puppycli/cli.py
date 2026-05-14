"""CLI entry point for PuppyCLI.

Usage:
    puppy               # Start server and open browser
    puppy --port 8765   # Custom port
    puppy --no-browser  # Don't auto-open browser
    puppy --setup       # Run configuration wizard
    puppy --update      # Update to latest from GitHub
    puppy --uninstall   # Uninstall PuppyCLI
"""
from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import threading
import time
import webbrowser
from pathlib import Path

import uvicorn


_REPO_URL = "https://github.com/Albert-Libra/PuppyCLI.git"


def _safe_print(msg: str) -> None:
    """Print safely on terminals that don't support Unicode."""
    try:
        print(msg)
    except UnicodeEncodeError:
        # Fall back to ASCII-safe version
        print(msg.encode("ascii", errors="replace").decode("ascii"))


def _safe_input(prompt: str) -> str:
    """Read a line from stdin safely."""
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        sys.exit(0)


def _run_setup_wizard(is_first_run: bool = True) -> None:
    """Interactive first-time setup wizard."""
    from puppycli.config import DEFAULT_CONFIG, Config

    config = Config()
    data = config.as_dict()

    print()
    _safe_print("=" * 56)
    if is_first_run:
        _safe_print("  PuppyCLI — Welcome! Let's get you set up.")
    else:
        _safe_print("  PuppyCLI — Setup Wizard")
    _safe_print("=" * 56)
    print()
    _safe_print("Press Enter to accept the [default] shown in brackets.")
    print()

    # 1. Data directory
    default_data_dir = str(Path.home() / "PuppyCLI")
    existing = data.get("data_dir", "") or default_data_dir
    _safe_print(f"[1/3] Data directory (sessions, knowledge, skills)")
    _safe_print(f"      [{existing}]")
    data_dir = _safe_input("> ").strip()
    if data_dir:
        config.set("data_dir", data_dir)
        _safe_print(f"      => {data_dir}")
    else:
        _safe_print(f"      => {existing} (default)")
    print()

    # 2. Python virtual environment
    existing_py = data.get("python_env", "")
    _safe_print(f"[2/3] Python virtual environment path")
    _safe_print(f"      Leave empty if you use the system Python.")
    hint = f" [{existing_py}]" if existing_py else " []"
    _safe_print(f"     {hint}")
    py_env = _safe_input("> ").strip()
    if py_env:
        config.set("python_env", py_env)
        _safe_print(f"      => {py_env}")
    elif not existing_py:
        _safe_print(f"      => (system Python)")
    else:
        _safe_print(f"      => {existing_py} (kept)")
    print()

    # 3. API Key (optional — can be set in Web UI)
    existing_key = data.get("api_key", "")
    masked = ""
    if existing_key:
        masked = existing_key[:8] + "..." if len(existing_key) > 8 else "***"
        _safe_print(f"[3/3] DeepSeek API key (current: {masked})")
    else:
        _safe_print(f"[3/3] DeepSeek API key (can also be set in Web UI)")
    _safe_print(f"      Get one at https://platform.deepseek.com/api_keys")
    api_key = _safe_input("> ").strip()
    if api_key:
        config.set("api_key", api_key)
        _safe_print(f"      => {api_key[:8]}... (saved)")
    elif existing_key:
        _safe_print(f"      => {masked} (kept)")
    else:
        _safe_print(f"      => (skipped — you can set it later in the Web UI)")
    print()

    _safe_print("=" * 56)
    _safe_print("  Setup complete! Starting PuppyCLI...")
    _safe_print("=" * 56)
    print()


def _run_update() -> None:
    """Update PuppyCLI from GitHub."""
    print()
    _safe_print("=" * 56)
    _safe_print("  PuppyCLI — Updating from GitHub")
    _safe_print("=" * 56)
    print()
    _safe_print(f"Repository: {_REPO_URL}")
    print()

    _safe_print(f"Running: pip install --upgrade git+{_REPO_URL}")
    print()

    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "install", "--upgrade", f"git+{_REPO_URL}"],
        )
        print()
        _safe_print("=" * 56)
        _safe_print("  Update complete! Run 'puppy' to start.")
        _safe_print("=" * 56)
    except subprocess.CalledProcessError:
        print()
        _safe_print("ERROR: Update failed. Check your network connection and try again.")
        sys.exit(1)


def _run_uninstall() -> None:
    """Interactive uninstall wizard."""
    from puppycli.config import Config

    config = Config()

    # Discover data directory
    custom_data = config.get("data_dir", "")
    config_dir = str(config._config_dir)
    data_dir = custom_data or config_dir

    # Also check ~/PuppyCLI if it exists
    legacy_dir = str(Path.home() / "PuppyCLI")

    print()
    _safe_print("=" * 56)
    _safe_print("  PuppyCLI — Uninstall")
    _safe_print("=" * 56)
    print()

    # Package removal
    _safe_print("This will uninstall the PuppyCLI package.")
    _safe_print(f"  pip uninstall puppycli")
    print()

    # Data directory
    if custom_data and Path(data_dir).exists():
        _safe_print(f"Your data directory (sessions, knowledge, skills):")
        _safe_print(f"  {data_dir}")
        if legacy_dir != data_dir and Path(legacy_dir).exists():
            _safe_print(f"Default config location:")
            _safe_print(f"  {legacy_dir}")
        print()
        _safe_print("You can keep your data for future reinstallation.")
    elif Path(legacy_dir).exists():
        _safe_print(f"Data directory:")
        _safe_print(f"  {legacy_dir}")
        print()

    print()
    _safe_print("Proceed with uninstall? [y/N]")
    confirm = _safe_input("> ").lower()
    if confirm not in ("y", "yes"):
        _safe_print("Aborted.")
        sys.exit(0)

    print()

    # Remove data?
    _safe_print("Also delete all local data?")
    _safe_print("This includes conversations, knowledge base, skills, and config. [y/N]")
    delete_data = _safe_input("> ").lower()
    if delete_data in ("y", "yes"):
        print()
        for d in [data_dir, legacy_dir]:
            p = Path(d)
            if p.exists():
                _safe_print(f"Removing {p} ...")
                shutil.rmtree(p, ignore_errors=True)

    # Uninstall package
    print()
    _safe_print("Uninstalling package ...")
    print()
    try:
        subprocess.check_call(
            [sys.executable, "-m", "pip", "uninstall", "puppycli", "-y"],
        )
        print()
        _safe_print("=" * 56)
        _safe_print("  PuppyCLI has been uninstalled.")
        _safe_print("  Thanks for trying it out!")
        _safe_print("=" * 56)
    except subprocess.CalledProcessError:
        _safe_print("WARNING: pip uninstall failed. You may need to run it manually:")
        _safe_print(f"  {sys.executable} -m pip uninstall puppycli")
        sys.exit(1)


def main() -> None:
    """Main entry point for the `puppy` command."""
    parser = argparse.ArgumentParser(
        prog="puppy",
        description="PuppyCLI - A local AI agent tool with browser-based GUI",
    )
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=8765,
        help="Port to run the server on (default: 8765)",
    )
    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    parser.add_argument(
        "--no-browser",
        "-n",
        action="store_true",
        help="Don't automatically open the browser",
    )
    parser.add_argument(
        "--setup",
        action="store_true",
        help="Run the configuration wizard before starting",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Update PuppyCLI to the latest version from GitHub",
    )
    parser.add_argument(
        "--uninstall",
        action="store_true",
        help="Uninstall PuppyCLI and optionally remove all data",
    )
    args = parser.parse_args()

    # --update and --uninstall are standalone operations (don't start server)
    if args.update:
        _run_update()
        return
    if args.uninstall:
        _run_uninstall()
        return

    # Run setup wizard on first run, or when --setup is passed
    from puppycli.config import Config

    config = Config()
    is_first_run = not config._file.exists()
    if args.setup or is_first_run:
        _run_setup_wizard(is_first_run=is_first_run)

    url = f"http://{args.host}:{args.port}"

    if not args.no_browser:
        threading.Thread(target=lambda: (time.sleep(1.5), webbrowser.open(url)), daemon=True).start()

    _safe_print(f"PuppyCLI starting at {url}")
    _safe_print("Press Ctrl+C to stop.")

    uvicorn.run(
        "puppycli.app:create_app",
        host=args.host,
        port=args.port,
        factory=True,
        log_level="info",
    )


if __name__ == "__main__":
    main()
