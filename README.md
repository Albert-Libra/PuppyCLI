# PuppyCLI

[中文版](./README_zh.md)

---

A local AI agent tool with a browser-based GUI, built on [openai-agents-python](https://github.com/openai/openai-agents-python). PuppyCLI connects to DeepSeek API and runs entirely on your Windows machine.

## Features

- **Browser GUI** — Clean, minimalist chat interface with Markdown, LaTeX, and image rendering
- **Streaming** — Real-time token streaming via WebSocket
- **Agent Skills** — Install community skills from [agentskills.io](https://agentskills.io) (path, GitHub, URL)
- **Knowledge Base** — Local persistent knowledge store with auto-search in every conversation
- **PDF Processing** — Extract text from PDFs via MinerU (local or cloud API)
- **PowerShell** — Execute commands directly from chat (`!Get-Date`)
- **Slash Commands** — `/help`, `/theme`, `/lang`, `/export`, `/model`, `/skill`, `/kb`, `/pdf` and more
- **Session Management** — Rename, delete, and switch between conversations
- **Bilingual** — Chinese / English UI toggle
- **Dark Mode** — Light and dark themes

## Installation

Requires Python 3.10+.

```bash
pip install git+https://github.com/Albert-Libra/PuppyCLI.git
```

## Quick Start

```bash
puppy
```

Opens your default browser at `http://127.0.0.1:8765`. Configure your DeepSeek API key in the Settings panel (⚙️).

```bash
# Custom port
puppy --port 8765

# Don't auto-open browser
puppy --no-browser
```

## Configuration

All settings are stored in `~/PuppyCLI/config.yaml`:

| Key | Description | Default |
|-----|-------------|---------|
| `api_key` | Your DeepSeek API key | — |
| `model` | Model name | `deepseek-chat` |
| `base_url` | API endpoint | `https://api.deepseek.com` |
| `data_dir` | Custom data directory | `~/PuppyCLI` |
| `python_env` | Python virtual env path | — |
| `mineru_token` | MinerU cloud API token | — |

## Data & Privacy

- All data is stored **locally** under `~/PuppyCLI/` (or a custom path via `data_dir`)
- Your API key is stored in `~/PuppyCLI/config.yaml` (plain text, local only)
- Conversation history is stored as JSONL files under `<data_dir>/sessions/`
- Knowledge base stored under `<data_dir>/knowledge/`
- **No telemetry, no analytics, no data leaves your machine** (except API calls to the LLM provider you configure)

## Architecture

```
puppycli/
├── agent/          AI agent runner & tools
├── server/         FastAPI REST + WebSocket
├── session/        Conversation persistence
├── skill/          Agent Skills manager
├── knowledge/      Local knowledge base
├── processing/     PDF & document processing
├── config.py       YAML configuration
├── cli.py          CLI entry point
├── app.py          FastAPI application
└── static/         Frontend (HTML/CSS/JS)
```

## Documentation

After starting the server, click 📖 in the top bar or visit `/help/`. Rebuild docs:

```bash
python scripts/build_docs.py
```

## Contributing

Issues and pull requests are welcome. Please keep the minimalist design philosophy.

## License

MIT
