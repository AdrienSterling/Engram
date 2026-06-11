"""Bilibili video extractor — subtitles, Whisper fallback, Gemini fallback."""

import logging
import re
from typing import Optional

import aiohttp

from engram.core.exceptions import ExtractorError
from engram.core.types import SourceType

from .base import BaseExtractor, ExtractionResult
from .gemini_youtube import get_gemini_analyzer
from .transcriber import get_transcriber

logger = logging.getLogger(__name__)


class BilibiliExtractor(BaseExtractor):
    """Bilibili video content extractor with 3-level fallback."""

    name = "bilibili"
    source_type = SourceType.BILIBILI

    URL_PATTERNS = [
        re.compile(r"(?:https?://)?(?:www\.)?bilibili\.com/video/(BV[a-zA-Z0-9]{10})"),
        re.compile(r"(?:https?://)?b23\.tv/([a-zA-Z0-9]+)"),
    ]

    BILIBILI_INFO_API = "https://api.bilibili.com/x/web-interface/view"
    BILIBILI_SUBTITLE_API = "https://api.bilibili.com/x/player/v2"

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None:
            self._session = aiohttp.ClientSession(
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Referer": "https://www.bilibili.com/",
                }
            )
        return self._session

    async def can_handle(self, url: str) -> bool:
        return self._extract_bvid(url) is not None

    def _extract_bvid(self, url: str) -> Optional[str]:
        for pattern in self.URL_PATTERNS:
            match = pattern.search(url)
            if match:
                return match.group(1)
        return None

    async def extract(self, url: str) -> ExtractionResult:
        bvid = self._extract_bvid(url)
        if not bvid:
            raise ExtractorError(f"Invalid Bilibili URL: {url}")

        logger.info(f"Extracting Bilibili video: {bvid}")

        try:
            title, cid, duration = await self._get_video_info(bvid)
            clean_url = f"https://www.bilibili.com/video/{bvid}"

            # Try subtitles first
            try:
                result = await self._extract_subtitles(bvid, cid)
                if result:
                    full_text, language = result
                    logger.info(f"Extracted Bilibili subtitles: {len(full_text)} chars, lang={language}")
                    return ExtractionResult(
                        title=title,
                        content=full_text,
                        source_type=SourceType.BILIBILI,
                        source_url=clean_url,
                        language=language,
                        duration=duration,
                        raw_data={"bvid": bvid, "cid": cid, "method": "subtitles"},
                    )
            except Exception as e:
                logger.info(f"No Bilibili subtitles: {e}")

            # Fallback 1: Whisper
            transcriber = get_transcriber()
            if transcriber.is_available:
                logger.info("Falling back to Whisper...")
                try:
                    full_text = await transcriber.transcribe(clean_url)
                    logger.info(f"Whisper transcription: {len(full_text)} chars")
                    return ExtractionResult(
                        title=title,
                        content=full_text,
                        source_type=SourceType.BILIBILI,
                        source_url=clean_url,
                        raw_data={"bvid": bvid, "method": "whisper"},
                    )
                except Exception as e:
                    logger.warning(f"Whisper failed: {e}")

            # Fallback 2: Gemini
            gemini = get_gemini_analyzer()
            if gemini.is_available:
                logger.info("Falling back to Gemini...")
                try:
                    full_text = await gemini.analyze_video(bvid)
                    return ExtractionResult(
                        title=title,
                        content=full_text,
                        source_type=SourceType.BILIBILI,
                        source_url=clean_url,
                        raw_data={"bvid": bvid, "method": "gemini"},
                    )
                except Exception as e:
                    logger.error(f"Gemini failed: {e}")

            raise ExtractorError("All extraction methods failed for Bilibili video")
        finally:
            await self.close()

    async def get_timestamped_transcript(self, bvid: str) -> Optional[str]:
        """Get timestamped transcript for enhanced summarization."""
        _, cid, _ = await self._get_video_info(bvid)

        # Try Bilibili subtitles with timestamps
        try:
            return await self._extract_subtitles_timestamped(bvid, cid)
        except Exception:
            pass

        # Whisper fallback with timestamps
        transcriber = get_transcriber()
        if transcriber.is_available:
            url = f"https://www.bilibili.com/video/{bvid}"
            try:
                return await transcriber.transcribe_with_timestamps(url)
            except Exception as e:
                logger.warning(f"Whisper timestamped fallback failed: {e}")

        return None

    async def _get_video_info(self, bvid: str) -> tuple[str, int, int]:
        """Get video title, cid, and duration."""
        session = await self._get_session()
        try:
            params = {"bvid": bvid}
            async with session.get(self.BILIBILI_INFO_API, params=params) as resp:
                if resp.status != 200:
                    return f"Bilibili Video {bvid}", 0, 0
                data = await resp.json()
                code = data.get("code", -1)
                if code != 0:
                    return f"Bilibili Video {bvid}", 0, 0
                video_data = data.get("data", {})
                title = video_data.get("title", f"Bilibili Video {bvid}")
                cid = video_data.get("cid", 0)
                duration = video_data.get("duration", 0)
                return title, cid, duration
        except Exception as e:
            logger.warning(f"Failed to get Bilibili video info: {e}")
            return f"Bilibili Video {bvid}", 0, 0

    async def _extract_subtitles(self, bvid: str, cid: int) -> Optional[tuple[str, str]]:
        """Extract Bilibili CC subtitles as plain text."""
        session = await self._get_session()
        params = {"bvid": bvid, "cid": cid}
        async with session.get(self.BILIBILI_SUBTITLE_API, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if data.get("code") != 0:
                return None

        subtitle_data = data.get("data", {}).get("subtitle", {})
        subtitles = subtitle_data.get("subtitles", [])
        if not subtitles:
            return None

        for sub in subtitles:
            sub_url = sub.get("subtitle_url")
            if not sub_url:
                continue
            if sub_url.startswith("//"):
                sub_url = "https:" + sub_url

            async with session.get(sub_url) as sub_resp:
                if sub_resp.status != 200:
                    continue
                sub_json = await sub_resp.json()
                body = sub_json.get("body", [])
                lines = [item.get("content", "") for item in body]
                lang = sub.get("lan_doc", "zh")
                return " ".join(lines), lang

        return None

    async def _extract_subtitles_timestamped(self, bvid: str, cid: int) -> Optional[str]:
        """Extract Bilibili CC subtitles with timestamps."""
        session = await self._get_session()
        params = {"bvid": bvid, "cid": cid}
        async with session.get(self.BILIBILI_SUBTITLE_API, params=params) as resp:
            if resp.status != 200:
                return None
            data = await resp.json()
            if data.get("code") != 0:
                return None

        subtitle_data = data.get("data", {}).get("subtitle", {})
        subtitles = subtitle_data.get("subtitles", [])
        if not subtitles:
            return None

        for sub in subtitles:
            sub_url = sub.get("subtitle_url")
            if not sub_url:
                continue
            if sub_url.startswith("//"):
                sub_url = "https:" + sub_url

            async with session.get(sub_url) as sub_resp:
                if sub_resp.status != 200:
                    continue
                sub_json = await sub_resp.json()
                body = sub_json.get("body", [])
                lines = []
                for item in body:
                    text = item.get("content", "").strip()
                    if not text:
                        continue
                    start = float(item.get("from", 0))
                    hh = int(start) // 3600
                    mm = (int(start) % 3600) // 60
                    ss = int(start) % 60
                    lines.append(f"[{hh:02d}:{mm:02d}:{ss:02d}] {text}")
                return "\n".join(lines)

        return None

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None
