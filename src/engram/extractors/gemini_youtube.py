"""
Gemini-based YouTube video analyzer.

Uses Google's Gemini API to directly analyze YouTube videos,
bypassing download restrictions.
"""

import logging
import asyncio
from typing import Optional

from engram.core.config import get_settings
from engram.core.exceptions import ExtractorError

logger = logging.getLogger(__name__)


class GeminiYouTubeAnalyzer:
    """
    Analyze YouTube videos using Gemini API.

    Gemini can directly process YouTube URLs without downloading,
    making it useful for videos with access restrictions.
    """

    def __init__(self):
        """Initialize analyzer."""
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        self.model = settings.gemini_model

        if not self.api_key:
            logger.warning("Gemini API key not configured")

    @property
    def is_available(self) -> bool:
        """Check if Gemini is available."""
        return bool(self.api_key)

    async def analyze_video(self, video_id: str, prompt: Optional[str] = None) -> str:
        """
        Analyze a YouTube video using Gemini.

        Args:
            video_id: YouTube video ID
            prompt: Custom prompt for analysis (optional)

        Returns:
            Analysis/summary of the video content
        """
        if not self.is_available:
            raise ExtractorError("Gemini API key not configured")

        try:
            from google import genai
            from google.genai import types
        except ImportError:
            raise ExtractorError("google-genai package not installed")

        video_url = f"https://www.youtube.com/watch?v={video_id}"

        if not prompt:
            prompt = (
                "Please provide a comprehensive summary of this video. "
                "Include the main topics discussed, key points, and any important details. "
                "Use the same language as the video content."
            )

        logger.info(f"Analyzing video with Gemini: {video_id}")

        try:
            client = genai.Client(api_key=self.api_key)

            # Run in thread pool since genai is sync
            loop = asyncio.get_event_loop()

            def do_analyze():
                response = client.models.generate_content(
                    model=self.model,
                    contents=[
                        types.Part(file_data=types.FileData(file_uri=video_url)),
                        types.Part(text=prompt),
                    ],
                )
                return response.text

            result = await loop.run_in_executor(None, do_analyze)

            if not result:
                raise ExtractorError("Gemini returned empty response")

            logger.info(f"Gemini analysis complete: {len(result)} chars")
            return result

        except Exception as e:
            error_msg = str(e)
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                raise ExtractorError("Gemini API quota exceeded, please try again later")
            elif "404" in error_msg or "NOT_FOUND" in error_msg:
                raise ExtractorError(f"Video not accessible via Gemini: {video_id}")
            else:
                raise ExtractorError(f"Gemini analysis failed: {error_msg}")


# Global instance
_analyzer: Optional[GeminiYouTubeAnalyzer] = None


def get_gemini_analyzer() -> GeminiYouTubeAnalyzer:
    """Get global analyzer instance."""
    global _analyzer
    if _analyzer is None:
        _analyzer = GeminiYouTubeAnalyzer()
    return _analyzer
