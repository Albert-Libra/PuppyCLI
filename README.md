# PuppyCLI

[中文版](./README_zh.md)

---

A local AI agent tool with a browser-based GUI, built on [openai-agents-python](https://github.com/openai/openai-agents-python). PuppyCLI connects to any OpenAI-compatible API (DeepSeek by default) and runs entirely on your Windows machine.

## Features

- **Browser GUI** — Clean, minimalist chat interface with Markdown, LaTeX (KaTeX), code highlighting, and image rendering
- **Streaming** — Real-time token streaming via WebSocket
- **Agent Skills** — Install community skills from [agentskills.io](https://agentskills.io) (local path, GitHub repo, or URL); auto-adapt CLI-oriented skills for the browser frontend
- **Knowledge Base** — Local persistent knowledge store with keyword-search scoring; auto-searched and injected into every conversation
- **PDF Processing** — Extract text from PDFs via MinerU (free local mode, or cloud API with token)
- **Web Search** — Search the internet via local MCP server or DuckDuckGo fallback (free, no configuration needed)
- **Web Fetch** — Extract readable text from any URL
- **PowerShell** — Execute commands directly from chat (`!Get-Date`); dangerous file-modifying commands require user confirmation
- **Slash Commands** — `/help`, `/theme`, `/lang`, `/export`, `/model`, `/skill`, `/kb`, `/pdf` and more
- **Session Management** — Create, rename, delete, and switch between conversations; automatic conversation summaries
- **Bilingual** — Chinese / English UI toggle
- **Dark Mode** — Light and dark themes

## Installation

Requires Python 3.10+.

```bash
pip install --no-cache-dir git+https://github.com/Albert-Libra/PuppyCLI.git
```

## Quick Start

```bash
puppy
```

Opens your default browser at `http://127.0.0.1:8765`. On first run, an interactive setup wizard guides you through configuration.

```bash
puppy --port 8080        # Custom port
puppy --host 0.0.0.0     # Bind to all interfaces
puppy --no-browser       # Don't auto-open browser
puppy --setup            # Re-run the configuration wizard
puppy --update           # Update to the latest version from GitHub
puppy --uninstall        # Uninstall PuppyCLI (optionally delete all data)
```

## Configuration

All settings are stored in `~/PuppyCLI/config.yaml`:

| Key | Description | Default |
|-----|-------------|---------|
| `api_key` | Your API key (DeepSeek or other OpenAI-compatible provider) | — |
| `model` | Model name | `deepseek-chat` |
| `base_url` | API endpoint | `https://api.deepseek.com` |
| `theme` | UI theme (`light` or `dark`) | `light` |
| `data_dir` | Custom data directory | `~/PuppyCLI` |
| `python_env` | Python virtual env path (for code execution) | — |
| `mineru_token` | MinerU cloud API token (optional; local mode works without it) | — |

API key, model, base URL, theme, Python env, and data directory can also be changed from the Settings panel (⚙️) in the web UI.

## Data & Privacy

- All data is stored **locally** under `~/PuppyCLI/` (or a custom path via `data_dir`)
- Your API key is stored in `~/PuppyCLI/config.yaml` (plain text, local only)
- Conversation history is stored as JSONL files under `<data_dir>/sessions/`
- Knowledge base stored under `<data_dir>/knowledge/`
- Installed skills stored under `<data_dir>/skills/`
- **No telemetry, no analytics, no data leaves your machine** (except API calls to the LLM provider and optional services you configure: MinerU cloud, MCP servers, DuckDuckGo)

## Architecture

```
puppycli/
├── agent/          AI agent runner & built-in tools (PowerShell, web search, web fetch, knowledge search, PDF)
├── server/         FastAPI REST API & WebSocket handler
├── session/        Conversation persistence (JSONL + metadata index)
├── skill/          Agent Skills manager (install, adapt, restore) & registry search
├── knowledge/      Local knowledge base (JSONL, keyword search with scoring)
├── processing/     PDF processing via MinerU (local or cloud)
├── providers/      MCP Streamable HTTP client for external tool servers
├── config.py       YAML configuration management
├── cli.py          CLI entry point (`puppy` command)
├── app.py          FastAPI application factory
├── update.py       Update checker (24h cache, GitHub version comparison)
└── static/         Frontend (HTML/CSS/JS — SPA)
```

## Documentation

After starting the server, click the 📖 icon in the top bar or visit `/help/`. To rebuild the API docs:

```bash
python scripts/build_docs.py
```

## Contributing

Issues and pull requests are welcome. Please keep the minimalist design philosophy.

## License

MIT
