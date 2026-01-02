"""
Engram main entry point.

Usage:
    python -m engram [command]

Commands:
    bot       Run the Telegram bot (default)
    test      Run a quick test
"""

import sys
import asyncio


def main():
    """Main entry point."""
    command = sys.argv[1] if len(sys.argv) > 1 else "bot"

    if command == "bot":
        from engram.platforms.telegram import run_bot
        asyncio.run(run_bot())

    elif command == "test":
        print("Engram is installed correctly!")
        print("Run 'python -m engram bot' to start the Telegram bot.")

    else:
        print(f"Unknown command: {command}")
        print("Available commands: bot, test")
        sys.exit(1)


if __name__ == "__main__":
    main()
