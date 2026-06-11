"""
Audio transcription service using Groq Whisper API.

Handles downloading audio from any video platform via yt-dlp
and transcribing via Groq with optional timestamps.
"""

import asyncio
import logging
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from groq import Groq

from engram.core.config import get_settings
from engram.core.exceptions import ExtractorError

logger = logging.getLogger(__name__)


class AudioTranscriber:
    """Transcribe audio using Groq Whisper API."""

    MAX_FILE_SIZE = 25 * 1024 * 1024

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.groq_api_key
        self.model = settings.groq_whisper_model

        if not self.api_key:
            logger.warning("Groq API key not configured, transcription disabled")

    @property
    def is_available(self) -> bool:
        return bool(self.api_key)

    async def transcribe(self, url: str) -> Optional[str]:
        """Download audio from URL and transcribe to plain text."""
        if not self.is_available:
            raise ExtractorError("Groq API key not configured")

        audio_path = await self._download_audio(url)
        if not audio_path:
            raise ExtractorError(f"Failed to download audio from: {url}")

        try:
            file_size = os.path.getsize(audio_path)
            logger.info(f"Audio file size: {file_size / 1024 / 1024:.1f} MB")

            if file_size > self.MAX_FILE_SIZE:
                raise ExtractorError(
                    f"Audio file too large ({file_size / 1024 / 1024:.1f} MB)"
                )

            transcript = await self._transcribe_audio(audio_path)
            logger.info(f"Transcription complete: {len(transcript)} chars")
            return transcript
        finally:
            self._cleanup(audio_path)

    async def transcribe_with_timestamps(self, url: str) -> Optional[str]:
        """Download audio from URL and return timestamped transcript.

        Returns:
            String format: "[00:01:23] text segment\n[00:02:45] next segment..."
            Or None if failed.
        """
        if not self.is_available:
            return None

        audio_path = await self._download_audio(url)
        if not audio_path:
            return None

        try:
            file_size = os.path.getsize(audio_path)
            if file_size > self.MAX_FILE_SIZE:
                logger.warning(f"Audio too large: {file_size / 1024 / 1024:.1f} MB")
                return None

            segments = await self._transcribe_verbose(audio_path)
            if not segments:
                return None

            lines = []
            for seg in segments:
                text = seg.get("text", "").strip()
                if not text:
                    continue
                start = int(seg.get("start", 0))
                hh = start // 3600
                mm = (start % 3600) // 60
                ss = start % 60
                lines.append(f"[{hh:02d}:{mm:02d}:{ss:02d}] {text}")

            result = "\n".join(lines)
            logger.info(f"Timestamped transcription: {len(lines)} segments, {len(result)} chars")
            return result
        finally:
            self._cleanup(audio_path)

    async def _download_audio(self, url: str) -> Optional[str]:
        """Download audio from any URL using yt-dlp."""
        import yt_dlp

        temp_dir = tempfile.mkdtemp()
        output_template = os.path.join(temp_dir, "audio.%(ext)s")

        ydl_opts = {
            "format": "worstaudio[ext=m4a]/worstaudio[ext=webm]/worstaudio",
            "outtmpl": output_template,
            "quiet": True,
            "no_warnings": True,
            "extract_flat": False,
            "match_filter": yt_dlp.utils.match_filter_func("duration < 1800"),
            "extractor_args": {"youtube": {"player_client": ["android"]}},
        }

        try:
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, lambda: self._do_download(ydl_opts, url))

            for file in os.listdir(temp_dir):
                if file.startswith("audio"):
                    return os.path.join(temp_dir, file)
            return None
        except Exception as e:
            logger.error(f"Failed to download audio: {e}")
            shutil.rmtree(temp_dir, ignore_errors=True)
            return None

    def _do_download(self, opts: dict, url: str):
        import yt_dlp

        with yt_dlp.YoutubeDL(opts) as ydl:
            ydl.download([url])

    async def _transcribe_audio(self, audio_path: str) -> str:
        """Transcribe to plain text."""
        client = Groq(api_key=self.api_key)
        loop = asyncio.get_event_loop()

        def do_transcribe():
            with open(audio_path, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=(Path(audio_path).name, audio_file.read()),
                    model=self.model,
                    response_format="text",
                )
                return transcription

        return await loop.run_in_executor(None, do_transcribe)

    async def _transcribe_verbose(self, audio_path: str) -> list[dict]:
        """Transcribe to verbose JSON with timestamped segments."""
        client = Groq(api_key=self.api_key)
        loop = asyncio.get_event_loop()

        def do_transcribe():
            with open(audio_path, "rb") as audio_file:
                result = client.audio.transcriptions.create(
                    file=(Path(audio_path).name, audio_file.read()),
                    model=self.model,
                    response_format="verbose_json",
                )
                return result.segments if hasattr(result, "segments") else []

        try:
            return await loop.run_in_executor(None, do_transcribe)
        except Exception as e:
            logger.warning(f"Verbose transcription failed: {e}")
            return []

    def _cleanup(self, audio_path: Optional[str]):
        if audio_path:
            temp_dir = os.path.dirname(audio_path)
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)


_transcriber: Optional[AudioTranscriber] = None


def get_transcriber() -> AudioTranscriber:
    global _transcriber
    if _transcriber is None:
        _transcriber = AudioTranscriber()
    return _transcriber
