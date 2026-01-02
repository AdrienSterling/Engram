#!/usr/bin/env python3
"""
Integration test for the full YouTube -> Summary pipeline.

Usage:
    python scripts/test_integration.py [youtube_url]

This tests:
1. YouTube transcript extraction
2. LLM summarization
3. Full pipeline flow
"""

import asyncio
import sys
import logging
import io

# Fix Windows console encoding
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Setup path
sys.path.insert(0, "src")

from engram.core.config import get_settings
from engram.core.logging import setup_logging
from engram.extractors import ExtractorRegistry
from engram.llm import get_llm


async def test_extraction_only(url: str):
    """Test just the extraction step."""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("STEP 1: Testing YouTube extraction")
    logger.info("=" * 50)

    registry = ExtractorRegistry()
    extractor = await registry.get_extractor(url)

    if extractor is None:
        logger.error("No extractor found for URL")
        return None

    result = await extractor.extract(url)

    logger.info(f"Title: {result.title}")
    logger.info(f"Language: {result.language}")
    logger.info(f"Content length: {len(result.content)} chars")

    return result


async def test_summarization(content: str, instruction: str = None):
    """Test LLM summarization."""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("STEP 2: Testing LLM summarization")
    logger.info("=" * 50)

    try:
        llm = get_llm()
        summary = await llm.summarize(content, instruction)

        logger.info("Summary generated successfully")
        print("\n" + "-" * 50)
        print("SUMMARY:")
        print("-" * 50)
        print(summary)
        print("-" * 50 + "\n")

        return summary

    except Exception as e:
        logger.error(f"LLM summarization failed: {e}")
        return None


async def test_full_pipeline(url: str, instruction: str = None):
    """Test the complete pipeline."""
    logger = logging.getLogger(__name__)
    logger.info("=" * 50)
    logger.info("FULL PIPELINE TEST")
    logger.info(f"URL: {url}")
    if instruction:
        logger.info(f"Instruction: {instruction}")
    logger.info("=" * 50)

    # Step 1: Extract
    result = await test_extraction_only(url)
    if result is None:
        return

    # Step 2: Summarize
    settings = get_settings()
    available_llms = settings.get_available_llms()

    if available_llms:
        logger.info(f"Using LLM: {settings.default_llm}")
        await test_summarization(result.content, instruction)
    else:
        logger.warning("Skipping summarization (no LLM API key configured)")

    logger.info("=" * 50)
    logger.info("Pipeline test completed!")
    logger.info("=" * 50)


async def main():
    # Setup
    setup_logging(level="INFO")
    logger = logging.getLogger(__name__)

    # Get URL and optional instruction
    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        # Default test video
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"

    instruction = sys.argv[2] if len(sys.argv) > 2 else None

    # Check configuration
    settings = get_settings()
    logger.info("Configuration:")
    logger.info(f"  Available LLMs: {settings.get_available_llms()}")
    logger.info(f"  Default LLM: {settings.default_llm}")

    # Run test
    await test_full_pipeline(url, instruction)


if __name__ == "__main__":
    asyncio.run(main())
