"""
Telegram bot main entry point.

Usage:
    python -m engram.platforms.telegram.bot
"""

import asyncio
import logging

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
)

from engram.core.config import get_settings
from engram.core.logging import setup_logging

from .handlers import (
    clear_handler,
    error_handler,
    help_handler,
    message_handler,
    save_handler,
    start_handler,
    status_handler,
)

logger = logging.getLogger(__name__)


def create_application() -> Application:
    """
    Create and configure the Telegram bot application.

    Returns:
        Configured Application instance
    """
    settings = get_settings()

    # Create application
    application = Application.builder().token(settings.telegram_token).build()

    # Register command handlers
    application.add_handler(CommandHandler("start", start_handler))
    application.add_handler(CommandHandler("help", help_handler))
    application.add_handler(CommandHandler("save", save_handler))
    application.add_handler(CommandHandler("clear", clear_handler))
    application.add_handler(CommandHandler("status", status_handler))

    # Handle all text messages and URLs
    application.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            message_handler,
        )
    )

    # Handle documents (PDF)
    application.add_handler(
        MessageHandler(
            filters.Document.ALL,
            message_handler,
        )
    )

    # Handle photos
    application.add_handler(
        MessageHandler(
            filters.PHOTO,
            message_handler,
        )
    )

    # Error handler
    application.add_error_handler(error_handler)

    logger.info("Telegram bot application configured")
    return application


async def run_bot():
    """Run the bot."""
    settings = get_settings()
    setup_logging(level=settings.log_level)

    logger.info("Starting Engram Telegram Bot...")
    logger.info(f"Available LLMs: {settings.get_available_llms()}")
    logger.info(f"Vault path: {settings.vault_path}")

    application = create_application()

    # Start polling
    await application.initialize()
    await application.start()
    await application.updater.start_polling(
        allowed_updates=Update.ALL_TYPES,
        drop_pending_updates=True,
    )

    logger.info("Bot is running. Press Ctrl+C to stop.")

    # Keep running until stopped
    try:
        # Wait forever
        await asyncio.Event().wait()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Shutting down...")
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()


def main():
    """Main entry point."""
    asyncio.run(run_bot())


if __name__ == "__main__":
    main()
