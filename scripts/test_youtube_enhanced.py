#!/usr/bin/env python3
"""
Test the enhanced YouTube summarization + screenshot flow.

Usage:
    python scripts/test_youtube_enhanced.py [youtube_url]

Tests:
1. Timestamped transcript extraction
2. Enhanced LLM summarization (structured Markdown + Screenshot markers)
3. Screenshot marker parsing
4. (Optional) Video download + ffmpeg frame extraction
"""

import asyncio
import io
import logging
import sys

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
sys.path.insert(0, "src")

from engram.core.config import get_settings
from engram.core.logging import setup_logging
from engram.extractors import ExtractorRegistry, YouTubeExtractor
from engram.extractors.screenshot import ScreenshotExtractor
from engram.llm import get_llm

logger = logging.getLogger(__name__)


async def test_enhanced(url: str, with_screenshots: bool = False):
    settings = get_settings()
    available = settings.get_available_llms()

    print("=" * 60)
    print("ENHANCED YOUTUBE SUMMARIZATION TEST")
    print(f"URL: {url}")
    print(f"Default LLM: {settings.default_llm}")
    print(f"Available LLMs: {available}")
    print("=" * 60)

    if not available:
        print("ERROR: No LLM configured. Set API keys in .env")
        return

    # Step 1: Get extractor
    registry = ExtractorRegistry()
    extractor = await registry.get_extractor(url)

    if extractor is None:
        print("ERROR: No extractor found for URL")
        return

    if not isinstance(extractor, YouTubeExtractor):
        print(f"SKIP: Not a YouTube URL (got {type(extractor).__name__})")
        return

    # Step 2: Extract basic info (title)
    print("\n[1/4] Extracting video title...")
    result = await extractor.extract(url)
    print(f"  Title: {result.title}")
    print(f"  Content length: {len(result.content)} chars")

    # Step 3: Get timestamped transcript
    print("\n[2/4] Getting timestamped transcript...")
    video_id = extractor._extract_video_id(url)
    timestamped = await extractor.get_timestamped_transcript(video_id)

    if not timestamped:
        print("  WARNING: No timestamped transcript, using normal summarization")
        llm = get_llm()
        summary = await llm.summarize(result.content)
        print(f"\n{'='*60}")
        print("SUMMARY (normal):")
        print(f"{'='*60}")
        print(summary)
        return

    print(f"  Timestamped lines: {len(timestamped.splitlines())}")
    print(f"  Timestamped chars: {len(timestamped)}")
    print(f"  First 3 lines:")
    for line in timestamped.splitlines()[:3]:
        print(f"    {line}")

    # Step 4: Enhanced summarization
    print("\n[3/4] Generating structured summary with screenshot markers...")
    llm = get_llm()

    try:
        summary = await llm.summarize_youtube(timestamped)
    except Exception as e:
        print(f"  ERROR: LLM summarization failed: {e}")
        print("  Falling back to normal summarization...")
        summary = await llm.summarize(result.content[:50000])

    print(f"  Summary length: {len(summary)} chars")

    # Parse screenshot markers
    markers = ScreenshotExtractor.parse_markers(summary)
    print(f"  Screenshot markers found: {len(markers)}")
    for marker, ts in markers:
        mm, ss = ts // 60, ts % 60
        print(f"    {marker} -> {mm:02d}:{ss:02d}")

    print(f"\n{'='*60}")
    print("STRUCTURED SUMMARY:")
    print(f"{'='*60}")
    print(summary)
    print(f"{'='*60}")

    # Step 5 (optional): Download video and extract frames
    if with_screenshots and markers:
        print("\n[4/4] Testing screenshot extraction...")
        import tempfile
        from pathlib import Path

        temp_dir = Path(tempfile.mkdtemp(prefix="engram_test_"))
        assets_dir = temp_dir / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        screenshotter = ScreenshotExtractor(assets_dir=assets_dir)
        video_path = await screenshotter.download_video(url)

        if video_path:
            print(f"  Downloaded: {video_path}")
            timestamps = [ts for _, ts in markers]
            frame_map = screenshotter.extract_frames(video_path, timestamps)

            if frame_map:
                print(f"  Frames extracted: {len(frame_map)}")
                for ts, path in frame_map.items():
                    print(f"    {path} ({path.stat().st_size} bytes)")

                final = screenshotter.replace_markers(summary, frame_map)
                print(f"\n  Final markdown (first 500 chars):")
                print(f"  {final[:500]}...")
            else:
                print("  WARNING: No frames extracted (ffmpeg may not be installed)")

            screenshotter.cleanup()
        else:
            print("  WARNING: Video download failed (network issue or blocked)")

        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)

    print("\nDONE.")


async def main():
    setup_logging(level="INFO")

    if len(sys.argv) > 1:
        url = sys.argv[1]
    else:
        url = input("Enter YouTube URL: ").strip()
        if not url:
            print("No URL provided.")
            return

    with_screenshots = "--screenshots" in sys.argv or "-s" in sys.argv

    await test_enhanced(url, with_screenshots)


if __name__ == "__main__":
    asyncio.run(main())
