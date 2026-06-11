"""APScheduler integration for periodic review triggers."""

import logging
from pathlib import Path

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from telegram.ext import Application

from engram.core.config import get_settings
from engram.skills.review.coach import ReviewCoach

logger = logging.getLogger(__name__)

_scheduler: AsyncIOScheduler | None = None


def _load_chat_id(settings) -> int | None:
    """Load persisted chat ID from vault."""
    chat_file = Path(settings.vault_path) / ".engram_chat_id"
    if chat_file.exists():
        try:
            return int(chat_file.read_text().strip())
        except (ValueError, OSError):
            pass
    return None


async def _send_daily_review(application: Application):
    """Send daily review notification with due items summary."""
    settings = get_settings()

    chat_id = _load_chat_id(settings)
    if not chat_id:
        logger.warning("Daily review: no chat_id saved yet, skipping")
        return

    coach = ReviewCoach(vault_path=settings.vault_path)
    due_items = coach.get_due_items()

    if not due_items:
        logger.info("Daily review: no items due")
        return

    logger.info(f"Daily review: {len(due_items)} items due")

    titles = "\n".join(
        f"  • {item['title']}（第 {item['review_count'] + 1} 次）" for item in due_items[:5]
    )

    more = f"\n  ...还有 {len(due_items) - 5} 条" if len(due_items) > 5 else ""

    message = (
        f"📚 今日复习提醒\n\n"
        f"以下内容需要复习：\n{titles}{more}\n\n"
        f"———\n"
        f"发送 /review 开始复习"
    )

    try:
        await application.bot.send_message(chat_id=chat_id, text=message)
    except Exception as e:
        logger.error(f"Failed to send daily review: {e}")


def setup_scheduler(application: Application):
    """Initialize and start the APScheduler for daily review."""
    global _scheduler

    settings = get_settings()
    hour = settings.review_hour
    minute = settings.review_minute

    _scheduler = AsyncIOScheduler()
    _scheduler.add_job(
        _send_daily_review,
        CronTrigger(hour=hour, minute=minute),
        args=[application],
        id="daily_review",
        name="Daily review prompt",
    )

    _scheduler.start()
    logger.info(f"Review scheduler started (daily at {hour:02d}:{minute:02d})")


def shutdown_scheduler():
    """Shutdown the scheduler gracefully."""
    global _scheduler
    if _scheduler:
        _scheduler.shutdown(wait=False)
        logger.info("Review scheduler stopped")
