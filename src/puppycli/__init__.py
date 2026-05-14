"""PuppyCLI - A local AI agent tool with browser-based GUI.

PuppyCLI is a pip-installable local AI assistant that runs in your browser.
Built on openai-agents-python, it connects to DeepSeek API and provides:

- Browser-based chat GUI with Markdown, LaTeX, and image rendering
- Streaming responses via WebSocket
- Agent Skills (agentskills.io standard)
- Local knowledge base with auto-search
- PDF processing via MinerU
- PowerShell command execution
- Slash commands for quick actions

Usage:
    pip install puppycli
    puppy                    # Start server and open browser
    puppy --port 8765        # Custom port
    puppy --no-browser       # Don't auto-open browser

Modules:
- ``puppycli.agent`` — AI agent runner and built-in tools
- ``puppycli.server`` — FastAPI REST API and WebSocket
- ``puppycli.session`` — Conversation persistence
- ``puppycli.config`` — YAML-based configuration
- ``puppycli.skill`` — Agent Skills management
- ``puppycli.knowledge`` — Local knowledge base
- ``puppycli.processing`` — PDF and document processing
"""

__version__ = "0.1.0"
