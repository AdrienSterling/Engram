# Engram

> AI-powered knowledge capture and internalization system
>
> Let knowledge leave real traces in your brain

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

[English](README.md) | [中文](README_CN.md)

## What is Engram?

**Engram** (noun): A hypothetical permanent change in the brain accounting for the existence of memory; a memory trace.

Engram is a personal knowledge assistant that helps you:
- **Capture** content from YouTube, articles, PDFs, and images
- **Organize** information into projects (for doing) or knowledge areas (for learning)
- **Internalize** knowledge through output commitments, not just collection
- **Output** to your personal website or other platforms

## Core Philosophy

> "Collecting is not learning. Knowledge without output is not knowledge."

Based on cognitive science principles:
- **Two Paths**: "Doing" (project-driven) vs "Understanding" (learning-driven)
- **Output Commitment**: Every knowledge area requires a commitment to produce something
- **7-Day Expiration**: Uncategorized items expire to prevent digital hoarding
- **Active Recall**: Track digestion status to ensure real internalization

## Features

- **Multi-source extraction**: YouTube, web articles, PDFs, images
- **Smart routing**: Assign content to projects or knowledge areas
- **Multiple LLM support**: OpenAI, Anthropic Claude, DeepSeek, Ollama
- **Multiple storage backends**: Obsidian (Git), Notion, Google Docs (planned)
- **Multiple platforms**: Telegram (now), Discord, CLI (planned)

## Quick Start

### Prerequisites

- Python 3.10+
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- OpenAI API Key (or other LLM provider)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourname/engram.git
cd engram

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings
```

### Running

```bash
# Run the bot
python -m engram.platforms.telegram.bot
```

### Docker

```bash
# Build and run with Docker Compose
docker compose up -d
```

## Architecture

```
src/engram/
├── core/           # Core types and config
├── llm/            # LLM abstraction layer
├── extractors/     # Content extractors
├── agents/         # Business logic agents
├── storage/        # Storage backends
└── platforms/      # Platform adapters (Telegram, etc.)
```

## Configuration

See [.env.example](.env.example) for all configuration options.

Key settings:
- `TELEGRAM_TOKEN`: Your Telegram bot token
- `VAULT_PATH`: Path to your Obsidian vault
- `OPENAI_API_KEY`: OpenAI API key

## Documentation

- [Architecture](docs/en/architecture.md)
- [Configuration](docs/en/configuration.md)
- [Deployment](docs/en/deployment.md)
- [Storage Backends](docs/en/storage-backends.md)

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## License

MIT License - see [LICENSE](LICENSE) for details.

## Acknowledgments

- Inspired by [Tiago Forte's PARA method](https://fortelabs.com/blog/para/)
- Built with [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
