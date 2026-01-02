"""
Audio transcription service using Groq Whisper API.

Handles downloading audio from YouTube and transcribing via Groq.
"""

import os
import logging
import tempfile
import asyncio
import shutil
from pathlib import Path
from typing import Optional

from groq import Groq

from engram.core.config import get_settings
from engram.core.exceptions import ExtractorError

logger = logging.getLogger(__name__)


class AudioTranscriber:
    """
    Transcribe audio using Groq Whisper API.

    Uses yt-dlp to download audio, then Groq for transcription.
    """

    # Groq file size limit (25MB for free tier)
    MAX_FILE_SIZE = 25 * 1024 * 1024

    def __init__(self):
        """Initialize transcriber."""
        settings = get_settings()
        self.api_key = settings.groq_api_key
        self.model = settings.groq_whisper_model

        if not self.api_key:
            logger.warning("Groq API key not configured, transcription disabled")

    @property
    def is_available(self) -> bool:
        """Check if transcription is available."""
        return bool(self.api_key)

    async def transcribe_youtube(self, video_id: str) -> Optional[str]:
        """
        Download and transcribe YouTube video audio.

        Args:
            video_id: YouTube video ID

        Returns:
            Transcription text or None if failed
        """
        if not self.is_available:
            raise ExtractorError("Groq API key not configured")

        logger.info(f"Downloading audio for video: {video_id}")

        # Download audio to temp file
        audio_path = await self._download_audio(video_id)

        if not audio_path:
            raise ExtractorError(f"Failed to download audio for video: {video_id}")

        try:
            # Check file size
            file_size = os.path.getsize(audio_path)
            logger.info(f"Audio file size: {file_size / 1024 / 1024:.1f} MB")

            if file_size > self.MAX_FILE_SIZE:
                raise ExtractorError(
                    f"Audio file too large ({file_size / 1024 / 1024:.1f} MB). "
                    f"Max: {self.MAX_FILE_SIZE / 1024 / 1024} MB"
                )

            # Transcribe
            logger.info(f"Transcribing with Groq Whisper ({self.model})...")
            transcript = await self._transcribe_audio(audio_path)

            logger.info(f"Transcription complete: {len(transcript)} chars")
            return transcript

        finally:
            # Clean up temp file and directory
            if audio_path:
                temp_dir = os.path.dirname(audio_path)
                if os.path.exists(temp_dir):
                    shutil.rmtree(temp_dir, ignore_errors=True)
                    logger.debug(f"Cleaned up temp directory: {temp_dir}")

    async def _download_audio(self, video_id: str) -> Optional[str]:
        """
        Download audio from YouTube video using yt-dlp.

        Args:
            video_id: YouTube video ID

        Returns:
            Path to downloaded audio file
        """
        import yt_dlp

        url = f"https://www.youtube.com/watch?v={video_id}"

        # Create temp directory
        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, "audio.%(ext)s")

        ydl_opts = {
            # Download smallest audio format (no ffmpeg needed)
            "format": "worstaudio[ext=m4a]/worstaudio[ext=webm]/worstaudio",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            # Limit duration to avoid huge files (30 min max)
            "match_filter": yt_dlp.utils.match_filter_func("duration < 1800"),
            # No postprocessors - skip ffmpeg requirement
            # Use Android client to bypass bot detection
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        }

        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._do_download(ydl_opts, url))

            # Find the downloaded file
            for file in os.listdir(temp_dir):
                if file.startswith("audio"):
                    return os.path.join(temp_dir, file)

            return None

        except Exception as e:
            logger.error(f"Failed to download audio: {e}")
            # Clean up temp dir on failure
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

    def _do_download(self, opts: dict, url: str):
        """Perform the actual download (sync)."""
        import yt_dlp
        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    async def _transcribe_audio(self, audio_path: str) -> str:
        """
        Transcribe audio file using Groq Whisper API.

        Args:
            audio_path: Path to audio file

        Returns:
            Transcription text
        """
        client = Groq(api_key=self.api_key)

        # Run in thread pool (Groq SDK is sync)
        loop = asyncio.get_event_loop()

        def do_transcribe():
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=(Path(audio_path).name, audio_file.read()),
                    model=self.model,
                    response_format="text",
                )
                return transcription

        result = await loop.run_in_executor(None, do_transcribe)
        return result


# Global instance
_transcriber: Optional[AudioTranscriber] = None


def get_transcriber() -> AudioTranscriber:
    """Get global transcriber instance."""
    global _transcriber
    if _transcriber is None:
        _transcriber = AudioTranscriber()
    return _transcriber
