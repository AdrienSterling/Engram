#!/usr/bin/env python3
"""
Quick test script for YouTube extractor.
Usage: python scripts/test_youtube.py [youtube_url]
"""

import asyncio
import sys
import logging
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Setup path
sys.path.insert(0, "src")

from engram.extractors.youtube import YouTubeExtractor
from engram.core.logging import setup_logging


async def main():
    # Setup logging
    setup_logging(level="DEBUG")
    logger = logging.getLogger(__name__)

    # Get URL from command line or use default
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default test video (Rick Astley - Never Gonna Give You Up)
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    logger.info(f"Testing YouTube extraction for: {url}")

    extractor = YouTubeExtractor()

    # Test can_handle
    can_handle = await extractor.can_handle(url)
    logger.info(f"Can handle: {can_handle}")

    if not can_handle:
        logger.error("URL not recognized as YouTube video")
        return

    # Test extraction
    try:
        result = await extractor.extract(url)

        print("\n" + "=" * 50)
        print("EXTRACTION RESULT")
        print("=" * 50)
        print(f"Title: {result.title}")
        print(f"Language: {result.language}")
        print(f"Duration: {result.duration}s")
        print(f"Content length: {len(result.content)} chars")
        print("\nFirst 500 chars of transcript:")
        print("-" * 50)
        print(result.content[:500])
        print("...")
        print("=" * 50)

    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
