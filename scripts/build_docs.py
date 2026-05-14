#!/usr/bin/env python3
"""Build PuppyCLI documentation using pdoc.

Generates cross-indexed HTML documentation from docstrings.
Output: docs/html/
"""
import subprocess
import sys
from pathlib import Path


def build_docs() -> None:
    """Build HTML documentation."""
    project_root = Path(__file__).parent.parent
    output_dir = project_root / "src" / "puppycli" / "static" / "docs"

    # Clean previous build
    if output_dir.exists():
        import shutil
        shutil.rmtree(output_dir)

    print("Building PuppyCLI documentation...")
    result = subprocess.run(
        [
            sys.executable, "-m", "pdoc",
            "-o", str(output_dir),
            "--logo", "/logo.png",
            "--footer-text", "PuppyCLI v0.1.0 — A local AI agent tool",
            "--search",
            "--show-source",
            "src/puppycli",
        ],
        cwd=str(project_root),
        capture_output=True,
        text=True,
    )

    if result.returncode != 0:
        print("ERROR:", result.stderr)
        sys.exit(1)

    # Post-process: scale down logo size
    for html_file in output_dir.rglob("*.html"):
        content = html_file.read_text(encoding="utf-8")
        content = content.replace("max-height:35vh", "max-height:12vh")
        html_file.write_text(content, encoding="utf-8")

    print(f"Documentation built: {output_dir}")
    print(f"  Entry point: {output_dir / 'index.html'}")


if __name__ == "__main__":
    build_docs()
