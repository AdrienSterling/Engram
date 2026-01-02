"""
YouTube content extractor.

References:
- https://github.com/jdepoix/youtube-transcript-api
- API changed in v1.2: uses instance-based approach
"""

import re
import logging
from typing import Optional
from urllib.parse import urlparse, parse_qs

from youtube_transcript_api import YouTubeTranscriptApi

from engram.core.types import SourceType
from engram.core.exceptions import ExtractorError
from .base import BaseExtractor, ExtractionResult
from .transcriber import get_transcriber

logger = logging.getLogger(__name__)


class YouTubeExtractor(BaseExtractor):
    """
    YouTube video transcript extractor.

    Uses youtube-transcript-api to fetch subtitles/transcripts.
    Supports multiple languages with fallback.
    """

    name = "youtube"
    source_type = SourceType.YOUTUBE

    # Supported URL patterns
    URL_PATTERNS = [
        r"(?:https?://)?(?:www\.)?youtube\.com/watch\?v=([a-zA-Z0-9_-]{11})",
        r"(?:https?://)?(?:www\.)?youtu\.be/([a-zA-Z0-9_-]{11})",
        r"(?:https?://)?(?:www\.)?youtube\.com/embed/([a-zA-Z0-9_-]{11})",
        r"(?:https?://)?(?:www\.)?youtube\.com/v/([a-zA-Z0-9_-]{11})",
    ]

    # Preferred languages for transcripts (in order of priority)
    PREFERRED_LANGUAGES = ["zh-Hans", "zh-Hant", "zh", "en", "ja", "ko"]

    def __init__(self):
        """Initialize YouTube extractor."""
        self._compiled_patterns = [re.compile(p) for p in self.URL_PATTERNS]
        self._api = YouTubeTranscriptApi()

    async def can_handle(self, url: str) -> bool:
        """Check if URL is a YouTube video."""
        return self._extract_video_id(url) is not None

    def _extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract video ID from various YouTube URL formats.

        Supports:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID

        Args:
            url: YouTube URL

        Returns:
            Video ID or None if not found
        """
        # Try regex patterns first
        for pattern in self._compiled_patterns:
            match = pattern.search(url)
            if match:
                return match.group(1)

        # Try parsing URL query parameters
        try:
            parsed = urlparse(url)
            if "youtube.com" in parsed.netloc:
                query_params = parse_qs(parsed.query)
                if "v" in query_params:
                    return query_params["v"][0]
        except Exception:
            pass

        return None

    async def extract(self, url: str) -> ExtractionResult:
        """
        Extract transcript from YouTube video.

        First tries to get subtitles, falls back to Whisper transcription.

        Args:
            url: YouTube video URL

        Returns:
            ExtractionResult with transcript

        Raises:
            ExtractorError if extraction fails
        """
        video_id = self._extract_video_id(url)
        if not video_id:
            raise ExtractorError(f"Invalid YouTube URL: {url}")

        logger.info(f"Extracting transcript for video: {video_id}")

        # Get video title first
        title = await self._get_video_title(video_id)

        # Try subtitle extraction first
        try:
            result = await self._extract_subtitles(video_id)
            if result:
                full_text, used_language, duration = result
                logger.info(
                    f"Extracted subtitles: {len(full_text)} chars, "
                    f"language={used_language}, duration={duration}s"
                )
                return ExtractionResult(
                    title=title,
                    content=full_text,
                    source_type=SourceType.YOUTUBE,
                    source_url=f"https://www.youtube.com/watch?v={video_id}",
                    language=used_language,
                    duration=duration,
                    raw_data={"video_id": video_id, "method": "subtitles"},
                )
        except Exception as e:
            logger.info(f"No subtitles available: {e}")

        # Fallback to Whisper transcription
        logger.info("Falling back to Whisper transcription...")
        transcriber = get_transcriber()

        if not transcriber.is_available:
            raise ExtractorError(
                "No subtitles available and Groq API key not configured. "
                "Set GROQ_API_KEY to enable audio transcription."
            )

        try:
            full_text = await transcriber.transcribe_youtube(video_id)

            logger.info(f"Transcribed via Whisper: {len(full_text)} chars")

            return ExtractionResult(
                title=title,
                content=full_text,
                source_type=SourceType.YOUTUBE,
                source_url=f"https://www.youtube.com/watch?v={video_id}",
                language=None,  # Whisper auto-detects
                duration=None,
                raw_data={"video_id": video_id, "method": "whisper"},
            )

        except Exception as e:
            logger.error(f"Whisper transcription failed: {e}")
            raise ExtractorError(f"Failed to transcribe video: {e}") from e

    async def _extract_subtitles(self, video_id: str) -> Optional[tuple[str, str, int]]:
        """
        Try to extract subtitles from YouTube video.

        Returns:
            Tuple of (text, language, duration) or None if no subtitles
        """
        transcript = None
        used_language = None

        # Try fetching with language preference
        try:
            transcript = self._api.fetch(video_id, languages=self.PREFERRED_LANGUAGES)
            used_language = self._detect_language(transcript)
            logger.debug(f"Found transcript with preferred language: {used_language}")
        except Exception:
            # Fallback: fetch any available transcript
            try:
                transcript = self._api.fetch(video_id)
                used_language = self._detect_language(transcript)
                logger.debug(f"Using fallback transcript: {used_language}")
            except Exception:
                return None

        if transcript is None:
            return None

        # Convert to raw data for processing
        transcript_data = transcript.to_raw_data()

        # Combine transcript segments into full text
        full_text = self._combine_transcript(transcript_data)

        # Calculate total duration
        duration = 0
        if transcript_data:
            last_segment = transcript_data[-1]
            duration = int(last_segment.get("start", 0) + last_segment.get("duration", 0))

        return full_text, used_language, duration

    def _detect_language(self, transcript) -> Optional[str]:
        """Detect language from transcript object."""
        try:
            # Try to get language from transcript metadata
            if hasattr(transcript, 'language'):
                return transcript.language
            if hasattr(transcript, 'language_code'):
                return transcript.language_code
        except Exception:
            pass
        return None

    def _combine_transcript(self, transcript_data: list[dict]) -> str:
        """
        Combine transcript segments into readable text.

        Args:
            transcript_data: List of transcript segments

        Returns:
            Combined transcript text
        """
        texts = []
        for segment in transcript_data:
            text = segment.get("text", "").strip()
            if text:
                # Clean up common artifacts
                text = text.replace("\n", " ")
                text = re.sub(r"\s+", " ", text)
                texts.append(text)

        return " ".join(texts)

    async def _get_video_title(self, video_id: str) -> str:
        """
        Get video title via YouTube oEmbed API.

        Args:
            video_id: YouTube video ID

        Returns:
            Video title
        """
        try:
            import aiohttp
            async with aiohttp.ClientSession() as session:
                oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
                async with session.get(oembed_url) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("title", f"YouTube Video {video_id}")
        except Exception as e:
            logger.warning(f"Failed to get video title: {e}")

        return f"YouTube Video {video_id}"
