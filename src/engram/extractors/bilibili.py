"""Bilibili video extractor — uses yt-dlp for info, subtitles, and downloads."""

import asyncio
import logging
import re
from typing import Optional

from engram.core.exceptions import ExtractorError
from engram.core.types import SourceType

from .base import BaseExtractor, ExtractionResult
from .transcriber import get_transcriber

logger = logging.getLogger(__name__)


class BilibiliExtractor(BaseExtractor):
    """Bilibili video content extractor.

    Uses yt-dlp for video info and subtitle extraction,
    with Whisper fallback for videos without subtitles.
    """

    name = "bilibili"
    source_type = SourceType.BILIBILI

    URL_PATTERNS = [
        re.compile(r"(?:https?://)?(?:www\.)?bilibili\.com/video/(BV[a-zA-Z0-9]{10})"),
        re.compile(r"(?:https?://)?b23\.tv/([a-zA-Z0-9]+)"),
    ]

    def __init__(self):
        pass

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

        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["zh-Hans", "zh", "en", "ai-zh", "ai-en"],
        }

        try:
            loop = asyncio.get_event_loop()

            def _extract_info():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(url, download=False)

            info = await loop.run_in_executor(None, _extract_info)
        except Exception as e:
            raise ExtractorError(f"Failed to extract Bilibili video info: {e}") from e

        title = info.get("title", f"Bilibili {bvid}")
        duration = info.get("duration", 0)
        clean_url = info.get("webpage_url", url)

        # Try to get subtitles from yt-dlp
        subtitles = info.get("subtitles") or {}
        auto_subtitles = info.get("automatic_captions") or {}

        sub_text = None
        sub_lang = None
        for lang in ["zh-Hans", "zh", "zh-CN", "ai-zh", "en"]:
            for sub_dict in [subtitles, auto_subtitles]:
                if lang in sub_dict:
                    try:
                        sub_list = sub_dict[lang]
                        if sub_list:
                            sub_info = sub_list[0] if isinstance(sub_list, list) else sub_list
                            sub_url = sub_info.get("url") if isinstance(sub_info, dict) else None
                            if not sub_url:
                                continue

                            # yt-dlp may need to download the subtitle
                            import aiohttp

                            async with aiohttp.ClientSession() as session:
                                async with session.get(sub_url) as resp:
                                    if resp.status == 200:
                                        raw = await resp.text()
                                        sub_text, sub_lang = self._parse_subtitle(raw, lang)
                                        if sub_text:
                                            break
                    except Exception:
                        continue
            if sub_text:
                break

        if sub_text:
            logger.info(f"Extracted Bilibili subtitles: {len(sub_text)} chars, lang={sub_lang}")
            return ExtractionResult(
                title=title,
                content=sub_text,
                source_type=SourceType.BILIBILI,
                source_url=clean_url,
                language=sub_lang,
                duration=duration,
                raw_data={"bvid": bvid, "method": "subtitles"},
            )

        # Fallback: Whisper
        transcriber = get_transcriber()
        if transcriber.is_available:
            logger.info("No subtitles, falling back to Whisper...")
            try:
                full_text = await transcriber.transcribe(clean_url)
                if full_text:
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

        raise ExtractorError("All extraction methods failed for Bilibili video")

    async def get_timestamped_transcript(self, bvid: str) -> Optional[str]:
        """Get timestamped transcript for enhanced summarization."""
        import yt_dlp

        ydl_opts = {
            "quiet": True,
            "no_warnings": True,
            "skip_download": True,
            "writesubtitles": True,
            "writeautomaticsub": True,
            "subtitleslangs": ["zh-Hans", "zh", "en", "ai-zh", "ai-en"],
        }

        try:
            loop = asyncio.get_event_loop()

            def _extract():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    return ydl.extract_info(f"https://www.bilibili.com/video/{bvid}", download=False)

            info = await loop.run_in_executor(None, _extract)
        except Exception:
            return None

        subtitles = info.get("subtitles") or {}
        auto_subtitles = info.get("automatic_captions") or {}

        for lang in ["zh-Hans", "zh", "zh-CN", "ai-zh", "en"]:
            for sub_dict in [subtitles, auto_subtitles]:
                if lang in sub_dict:
                    try:
                        sub_info = sub_dict[lang][0]
                        sub_url = sub_info.get("url") if isinstance(sub_info, dict) else None
                        if not sub_url:
                            continue

                        import aiohttp

                        async with aiohttp.ClientSession() as session:
                            async with session.get(sub_url) as resp:
                                if resp.status == 200:
                                    raw = await resp.text()
                                    lines = self._parse_subtitle_timestamped(raw)
                                    if lines:
                                        return "\n".join(lines)
                    except Exception:
                        continue

        # Whisper fallback with timestamps
        transcriber = get_transcriber()
        if transcriber.is_available:
            url = f"https://www.bilibili.com/video/{bvid}"
            try:
                return await transcriber.transcribe_with_timestamps(url)
            except Exception:
                pass

        return None

    def _parse_subtitle(self, raw: str, lang: str) -> tuple[Optional[str], Optional[str]]:
        """Parse subtitle content from various formats (JSON, SRT, VTT)."""
        # Try JSON format (youtube transcript api style)
        try:
            import json

            data = json.loads(raw)
            if isinstance(data, dict):
                events = data.get("events") or data.get("body") or []
                texts = []
                for ev in events:
                    segs = ev.get("segs") or []
                    for seg in segs:
                        text = seg.get("utf8", "")
                        if text:
                            texts.append(text)
                if texts:
                    return " ".join(texts), lang
        except (json.JSONDecodeError, TypeError):
            pass

        # Try SRT format
        srt_lines = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line or line.isdigit() or "-->" in line:
                continue
            srt_lines.append(line)
        if srt_lines:
            return " ".join(srt_lines), lang

        return None, None

    def _parse_subtitle_timestamped(self, raw: str) -> list[str]:
        """Parse subtitle with timestamps to [hh:mm:ss] text format."""
        try:
            import json

            data = json.loads(raw)
            if isinstance(data, dict):
                events = data.get("events") or data.get("body") or []
                lines = []
                for ev in events:
                    start = float(ev.get("tStartMs", 0)) / 1000
                    segs = ev.get("segs") or []
                    text = "".join(seg.get("utf8", "") for seg in segs)
                    if text.strip():
                        hh = int(start) // 3600
                        mm = (int(start) % 3600) // 60
                        ss = int(start) % 60
                        lines.append(f"[{hh:02d}:{mm:02d}:{ss:02d}] {text.strip()}")
                return lines
        except (json.JSONDecodeError, TypeError):
            pass

        # Try SRT format with timestamps
        import re as re_mod

        srt_lines = []
        current_time = ""
        for line in raw.split("\n"):
            line = line.strip()
            time_match = re_mod.match(r"(\d{2}):(\d{2}):(\d{2})[.,]", line)
            if time_match:
                current_time = f"{time_match.group(1)}:{time_match.group(2)}:{time_match.group(3)}"
            elif line and not line.isdigit() and "-->" not in line:
                if current_time:
                    srt_lines.append(f"[{current_time}] {line}")
        return srt_lines
