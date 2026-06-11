# Sprint 1: Skills Framework + YouTube Monitor

**Status**: Not started
**Branch**: `sprint-1-skills`
**Estimated effort**: 2-3 sessions

---

## Goal

Transform Engram from a monolithic Telegram handler into a modular skills-based architecture, then implement the first new skill: YouTube Channel Monitor for comment marketing.

## Background

Engram currently has all business logic in `platforms/telegram/handlers.py`. To support multiple independent features (YouTube monitoring, coaching, etc.) we need a plugin/skills system where each feature is self-contained and can be triggered by Telegram commands OR scheduled cron.

The YouTube Monitor skill supports AstroBazi's growth strategy: monitor astrology/philosophy YouTube channels in 4 languages (EN, FR, ES, PT), detect new videos, generate contextual comments via LLM, and notify the user via Telegram for manual posting.

---

## Phase 1: Skills Framework (~200 lines)

### 1.1 Create `skills/base.py`

```python
from abc import ABC, abstractmethod
from typing import Optional

class BaseSkill(ABC):
    """Base class for all Engram skills."""
    
    name: str                           # unique id: "youtube_monitor"
    description: str                    # human-readable
    commands: list[str] = []            # telegram commands: ["/monitor"]
    schedulable: bool = False           # supports cron?
    schedule: Optional[str] = None      # cron expr: "*/30 * * * *"
    
    @abstractmethod
    async def handle_command(self, command: str, args: str, context) -> str:
        """Handle a Telegram command. Return response text."""
        
    async def handle_message(self, text: str, context) -> Optional[str]:
        """Handle free text. Return None to pass to next skill."""
        return None
    
    async def on_schedule(self):
        """Called by scheduler when cron fires."""
        pass
    
    async def setup(self):
        """Initialize skill (load data, etc). Called once at startup."""
        pass
    
    async def teardown(self):
        """Cleanup. Called on shutdown."""
        pass
```

### 1.2 Create `skills/registry.py`

- `SkillRegistry` class that:
  - Registers skills by name
  - Routes `/command` → correct skill
  - Provides `get_scheduled_skills()` for scheduler
  - Auto-discovers skills from `skills/` subpackages (optional, can be explicit)

### 1.3 Create `scheduler/manager.py`

- Use `apscheduler` (AsyncIOScheduler)
- On startup: iterate `registry.get_scheduled_skills()`, add cron jobs
- Each job calls `skill.on_schedule()`
- Needs access to Telegram bot for sending notifications
- Add `apscheduler` to `requirements.txt`

### 1.4 Integrate into `platforms/telegram/bot.py`

- In `create_application()`:
  - Initialize `SkillRegistry`, register all skills
  - Start `SchedulerManager`
  - Add a generic `CommandHandler` that routes to skills
- `handlers.py` becomes a thin router:
  - Known commands → skill.handle_command()
  - URLs → existing extract flow (or SummarizeSkill)
  - Free text → skill.handle_message() chain, then existing followup

### 1.5 Refactor existing summarize into `skills/summarize/`

- Move URL handling + followup logic from `handlers.py` → `SummarizeSkill`
- Keep the same behavior, just relocate
- `handlers.py` should only do routing after this

---

## Phase 2: YouTube Monitor Skill (~400 lines)

### 2.1 Create `skills/youtube_monitor/`

```
skills/youtube_monitor/
├── __init__.py
├── skill.py           # YouTubeMonitorSkill (BaseSkill)
├── rss.py             # RSS feed polling via feedparser
├── channels.py        # Channel database (JSON file)
├── comment_gen.py     # LLM comment generation
└── prompts/
    ├── comment_en.md  # English comment templates
    ├── comment_fr.md  # French
    ├── comment_es.md  # Spanish
    └── comment_pt.md  # Portuguese
```

### 2.2 `rss.py` — RSS Feed Monitor

```python
import feedparser
import aiohttp

YOUTUBE_RSS = "https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"

class RSSMonitor:
    def __init__(self, seen_db_path: str):
        self.seen_ids: set[str] = set()  # loaded from JSON file
    
    async def check_channel(self, channel_id: str) -> list[dict]:
        """Check RSS feed, return new videos (not seen before)."""
        # Parse feed, compare video IDs against seen_ids
        # Return list of {video_id, title, published, link}
    
    def mark_seen(self, video_id: str):
        """Mark video as processed."""
        
    def save(self):
        """Persist seen_ids to disk."""
```

- Add `feedparser` to `requirements.txt`
- RSS is free, no API quota, updates every 15 minutes
- Store seen video IDs in a JSON file (simple, no DB needed)

### 2.3 `channels.py` — Channel Database

```json
// channels.json
[
  {
    "channel_id": "UCxxxxxxx",
    "name": "AstrologiePratique",
    "language": "fr",
    "niche": "astrology",
    "subscribers": 42000,
    "added_at": "2026-04-05",
    "active": true
  }
]
```

- CRUD operations via Telegram commands
- Stored as JSON file in data directory
- Admin-only (check Telegram user ID)

### 2.4 `comment_gen.py` — Comment Generation

**Key constraint: Save tokens. Only use title + description + subtitles (first 2000 chars). NO audio transcription.**

```python
class CommentGenerator:
    def __init__(self, llm: BaseLLM):
        self.llm = llm
    
    async def generate(
        self,
        video_title: str,
        video_description: str,
        subtitles: Optional[str],  # first 2000 chars only
        language: str,             # "fr", "en", "es", "pt"
        channel_name: str,
    ) -> list[str]:
        """Generate 3 comment variants."""
        # Load prompt template for language
        # Call LLM (use DeepSeek for cost savings)
        # Return 3 comments: [value, question, pure_value_no_promo]
```

**Getting video metadata WITHOUT heavy extraction:**

| Data | Source | Cost |
|------|--------|------|
| Title | RSS feed (already have it) | $0 |
| Description | YouTube oEmbed API or yt-dlp `--skip-download --print description` | $0 |
| Subtitles (first 2000 chars) | `youtube-transcript-api` (already a dependency) | $0 |

**Do NOT call:** Whisper, Gemini, yt-dlp audio download.

### 2.5 `skill.py` — Main Skill

```python
class YouTubeMonitorSkill(BaseSkill):
    name = "youtube_monitor"
    description = "Monitor YouTube channels and generate comments"
    commands = ["/monitor", "/channels", "/add_channel", "/remove_channel"]
    schedulable = True
    schedule = "*/30 * * * *"  # every 30 minutes
    
    async def setup(self):
        self.rss = RSSMonitor(seen_db_path="data/seen_videos.json")
        self.channels = ChannelDB(path="data/channels.json")
        self.comment_gen = CommentGenerator(llm=get_llm("deepseek"))
    
    async def on_schedule(self):
        """Called every 30 min: check all channels for new videos."""
        for channel in self.channels.get_active():
            new_videos = await self.rss.check_channel(channel.channel_id)
            for video in new_videos:
                # Get subtitles (light, no audio)
                subtitles = await self._get_subtitles_light(video.video_id)
                # Generate comments
                comments = await self.comment_gen.generate(
                    video_title=video.title,
                    video_description=await self._get_description(video.video_id),
                    subtitles=subtitles[:2000] if subtitles else None,
                    language=channel.language,
                    channel_name=channel.name,
                )
                # Send to Telegram with inline keyboard
                await self._notify(video, channel, comments)
                self.rss.mark_seen(video.video_id)
        self.rss.save()
    
    async def handle_command(self, command, args, context):
        if command == "/monitor":
            return self._format_status()
        elif command == "/channels":
            return self._format_channel_list()
        elif command == "/add_channel":
            return await self._add_channel(args)
        elif command == "/remove_channel":
            return await self._remove_channel(args)
```

### 2.6 Telegram Notification Format

```
📺 New: AstrologiePratique (42K) 🇫🇷
⏰ 1h ago
🎬 "Comment interpréter votre thème astral chinois"

💬 Comments:

1️⃣ [Value + soft CTA]
"Merci pour cette analyse ! En tant que passionnée 
d'astrologie orientale, le Bazi apporte un éclairage 
complémentaire aux Cinq Éléments..."

2️⃣ [Question]
"Superbe vidéo ! Avez-vous exploré les parallèles 
entre l'astrologie occidentale et le Bazi ?"

3️⃣ [Pure value]
"Le passage sur les transits est brillant..."

[1️⃣ Copy] [2️⃣ Copy] [3️⃣ Copy] [⏭ Skip]
```

Use `InlineKeyboardMarkup` with callback queries. On button press, copy comment text to clipboard (or send as a separate message for easy copy on mobile).

---

## Phase 3: Deployment

### 3.1 Dependencies to add

```
# requirements.txt additions
feedparser>=6.0.0
apscheduler>=3.10.0
```

### 3.2 Config additions

```bash
# .env additions
ADMIN_USER_ID=123456789         # Telegram user ID for admin commands
MONITOR_NOTIFY_CHAT_ID=123456789 # Where to send notifications
YOUTUBE_MONITOR_ENABLED=true
YOUTUBE_MONITOR_INTERVAL=30      # minutes
```

### 3.3 Data persistence

- `data/channels.json` — channel list (mount as Docker volume)
- `data/seen_videos.json` — processed video IDs
- Docker volume: add `- /opt/app/engram-data:/app/data` to docker-compose.yml

### 3.4 Docker changes

```yaml
# docker-compose.yml addition
volumes:
  - /opt/app/obsidian-vault:/vault
  - /opt/app/engram-data:/app/data    # NEW: skill data persistence
```

---

## Future: Coach Skill (Sprint 2, architecture only)

```
skills/coach/
├── skill.py       # CoachSkill(BaseSkill)
├── goals.py       # Goal CRUD (JSON or SQLite)
├── review.py      # Daily review prompts
└── prompts/
    └── review.md  # Review conversation template
```

Commands: `/goal`, `/progress`, `/review`
Schedule: `0 21 * * *` (daily 9pm review reminder)
Storage: JSON file in `data/` or extend BaseStorage

The Skills framework from Phase 1 makes this trivial to add — just create the skill directory, implement BaseSkill, and register it.

---

## Files Changed Summary

| Action | File | Description |
|--------|------|-------------|
| NEW | `src/engram/skills/__init__.py` | Skills package |
| NEW | `src/engram/skills/base.py` | BaseSkill ABC |
| NEW | `src/engram/skills/registry.py` | SkillRegistry |
| NEW | `src/engram/skills/summarize/skill.py` | Refactored from handlers |
| NEW | `src/engram/skills/youtube_monitor/skill.py` | Main skill |
| NEW | `src/engram/skills/youtube_monitor/rss.py` | RSS polling |
| NEW | `src/engram/skills/youtube_monitor/channels.py` | Channel DB |
| NEW | `src/engram/skills/youtube_monitor/comment_gen.py` | LLM comments |
| NEW | `src/engram/skills/youtube_monitor/prompts/*.md` | Templates |
| NEW | `src/engram/scheduler/__init__.py` | Scheduler package |
| NEW | `src/engram/scheduler/manager.py` | APScheduler integration |
| EDIT | `src/engram/platforms/telegram/bot.py` | Register skills + scheduler |
| EDIT | `src/engram/platforms/telegram/handlers.py` | Thin router |
| EDIT | `src/engram/core/config.py` | Add skill-related settings |
| EDIT | `requirements.txt` | Add feedparser, apscheduler |
| EDIT | `docker-compose.yml` | Add data volume |

---

## Acceptance Criteria

- [ ] `BaseSkill` ABC with command, message, schedule handlers
- [ ] `SkillRegistry` routes commands to correct skill
- [ ] `SchedulerManager` fires `on_schedule()` via APScheduler
- [ ] Existing summarize flow works identically after refactor
- [ ] `/add_channel <url>` adds channel to monitor list
- [ ] `/channels` lists monitored channels
- [ ] New videos detected within 30 minutes of upload
- [ ] 3 comment variants generated per video (title+desc+subtitles only, no Whisper/Gemini)
- [ ] Telegram notification with inline copy buttons
- [ ] Data persists across Docker restarts (volume mount)
- [ ] Token cost < $0.01/day for 10 new videos
