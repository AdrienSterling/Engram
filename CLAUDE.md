# CLAUDE.md — Engram

## What is Engram

AI-powered knowledge capture and internalization bot. Users send links (YouTube, articles) via Telegram, get AI summaries, can ask follow-up questions, and save notes to Obsidian.

## Development Commands

```bash
# Local development
cd "D:\AI Coding\Engram"
venv\Scripts\python.exe -m engram bot

# Docker (production)
docker compose up -d

# Tests
venv\Scripts\python.exe -m pytest tests/ -v

# Lint
venv\Scripts\python.exe -m ruff check src/
venv\Scripts\python.exe -m black src/
```

## Architecture

```
src/engram/
├── core/              # Types, config (pydantic-settings), exceptions, logging
│   ├── config.py      # Settings from .env (Telegram, LLM keys, storage)
│   ├── types.py       # Material, Message, LLMResponse, Idea, KnowledgeArea
│   └── exceptions.py  # ExtractorError, LLMError, ConfigError, StorageError
│
├── extractors/        # Content extraction (Registry pattern)
│   ├── base.py        # BaseExtractor ABC → can_handle(url) + extract(url)
│   ├── registry.py    # ExtractorRegistry — auto-routes URLs to extractors
│   ├── youtube.py     # Subtitles → Whisper → Gemini (3-level fallback)
│   ├── article.py     # Web articles via newspaper3k
│   ├── transcriber.py # Groq Whisper STT
│   └── gemini_youtube.py # Gemini video analysis fallback
│
├── llm/               # LLM providers (Router pattern)
│   ├── base.py        # BaseLLM ABC → chat() + summarize() + vision()
│   ├── openai.py      # OpenAI-compatible (also serves DeepSeek)
│   └── router.py      # LLMRouter — provider selection + fallback
│
├── platforms/
│   └── telegram/      # Telegram bot (python-telegram-bot)
│       ├── bot.py     # Application setup, handler registration, polling
│       └── handlers.py # All command + message handlers
│
├── storage/           # Storage backends (Factory pattern)
│   ├── base.py        # BaseStorage ABC
│   └── backends/
│       └── obsidian/  # Git-backed Obsidian vault
│
├── prompts/           # Prompt templates (placeholder, not yet used)
└── __main__.py        # Entry point: `python -m engram bot`
```

## Key Design Patterns

- **Registry pattern**: ExtractorRegistry auto-routes URLs → extractors
- **Router pattern**: LLMRouter manages providers with fallback
- **Factory pattern**: Storage backends via factory
- **ABC everywhere**: BaseExtractor, BaseLLM, BaseStorage — extend via subclass
- **Global singletons**: `get_llm()`, `get_settings()`, `get_storage()`
- **Session state**: `context.user_data['session']` for per-user Telegram state

## Configuration (.env)

```bash
TELEGRAM_TOKEN=...
VAULT_PATH=/vault

# LLM (at least one required)
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-4
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-chat
ANTHROPIC_API_KEY=...

# Optional fallbacks for YouTube
GROQ_API_KEY=...          # Whisper STT
GEMINI_API_KEY=...        # Gemini video analysis

DEFAULT_LLM=openai        # or deepseek
```

## Deployment

- Production: Docker on Hetzner (`135.181.193.151`)
- Container: `engram-bot` (alongside AstroBazi containers)
- Vault: `/opt/app/obsidian-vault` mounted as `/vault`
- Image: `ghcr.io/adriensterling/engram:latest`
- CI: Push to `main` → GitHub Actions build + deploy

## Evolution Roadmap

Engram is evolving from a simple summarization bot into a modular **personal AI agent**. See `.claude/specs/` for active sprint specs.

### Planned Architecture: Skills System

```
src/engram/
├── skills/                  # Modular skill system
│   ├── base.py              # BaseSkill ABC
│   ├── registry.py          # SkillRegistry (auto-discovery)
│   ├── summarize/           # Existing summarize (refactored from handlers)
│   ├── youtube_monitor/     # YouTube channel monitoring + comment gen
│   └── coach/               # Personal goals & review (future)
├── scheduler/               # APScheduler for cron-triggered skills
└── ...existing modules
```

Each skill is self-contained, independently testable, and can be triggered by Telegram commands or scheduled cron.
