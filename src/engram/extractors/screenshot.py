"""
Video screenshot extraction using yt-dlp + ffmpeg.

Downloads video, extracts frames at marked timestamps,
replaces Screenshot-[hh:mm:ss] markers with actual image references.
"""

import asyncio
import logging
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

SCREENSHOT_MARKER_PATTERN = re.compile(
    r"Screenshot-\[(\d{2}):(\d{2}):(\d{2})\]"
)


class ScreenshotExtractor:
    """Downloads video and extracts screenshots at specified timestamps."""

    MAX_VIDEO_SIZE_MB = 200
    MAX_DOWNLOAD_SECONDS = 600

    def __init__(self, assets_dir: Path):
        """
        Args:
            assets_dir: Directory to save screenshot images
        """
        self.assets_dir = Path(assets_dir)
        self.assets_dir.mkdir(parents=True, exist_ok=True)
        self._temp_dir: Optional[Path] = None
        self._video_path: Optional[Path] = None

    @property
    def temp_dir(self) -> Path:
        if self._temp_dir is None:
            self._temp_dir = Path(tempfile.mkdtemp(prefix="engram_screenshot_"))
        return self._temp_dir

    @staticmethod
    def parse_markers(markdown: str) -> list[tuple[str, int]]:
        """
        Find all Screenshot-[hh:mm:ss] markers in markdown.

        Returns:
            List of (full_marker_string, total_seconds) tuples
        """
        results = []
        for match in SCREENSHOT_MARKER_PATTERN.finditer(markdown):
            hh, mm, ss = int(match.group(1)), int(match.group(2)), int(match.group(3))
            total_seconds = hh * 3600 + mm * 60 + ss
            results.append((match.group(0), total_seconds))
        return results

    async def download_video(self, url: str) -> Optional[Path]:
        """
        Download video from URL using yt-dlp.

        Returns:
            Path to downloaded video file, or None if download fails
        """
        try:
            import yt_dlp

            output_template = str(self.temp_dir / "%(id)s.%(ext)s")
            ydl_opts = {
                "format": "best[height<=720]/best",
                "outtmpl": output_template,
                "quiet": True,
                "no_warnings": True,
                "extractor_args": {"youtube": {"player_client": ["android"]}},
                "max_filesize": self.MAX_VIDEO_SIZE_MB * 1024 * 1024,
                "socket_timeout": self.MAX_DOWNLOAD_SECONDS,
            }

            loop = asyncio.get_running_loop()

            def _download():
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    return ydl.prepare_filename(info)

            filename = await loop.run_in_executor(None, _download)

            video_path = Path(filename)
            if video_path.exists():
                self._video_path = video_path
                logger.info(f"Downloaded video: {video_path} ({video_path.stat().st_size / 1024 / 1024:.1f}MB)")
                return video_path

            possible = list(self.temp_dir.glob("*"))
            if possible:
                self._video_path = possible[0]
                return self._video_path

            return None

        except Exception as e:
            logger.warning(f"Video download failed: {e}")
            return None

    def extract_frames(
        self, video_path: Path, timestamps: list[int], prefix: str = "screenshot"
    ) -> dict[int, Path]:
        """
        Extract frames from video at given timestamps using ffmpeg.

        Args:
            video_path: Path to video file
            timestamps: List of timestamps in seconds
            prefix: Filename prefix for screenshots

        Returns:
            Dict mapping timestamp -> output image path
        """
        frame_map = {}

        for i, ts in enumerate(timestamps):
            mm = ts // 60
            ss = ts % 60
            filename = f"{prefix}_{mm:02d}_{ss:02d}.jpg"
            output_path = self.assets_dir / filename

            cmd = [
                "ffmpeg",
                "-ss", str(ts),
                "-i", str(video_path),
                "-frames:v", "1",
                "-q:v", "2",
                str(output_path),
                "-y",
                "-loglevel", "error",
            ]

            logger.info(f"Extracting frame at {mm:02d}:{ss:02d} ({ts}s) -> {output_path}")

            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                if result.returncode == 0 and output_path.exists():
                    frame_map[ts] = output_path
                    logger.info(f"Screenshot saved: {output_path}")
                else:
                    logger.warning(
                        f"ffmpeg failed for ts={ts}: {result.stderr[:200]}"
                    )
            except subprocess.TimeoutExpired:
                logger.warning(f"ffmpeg timeout at ts={ts}")
            except FileNotFoundError:
                logger.error("ffmpeg not found, is it installed?")
                break
            except Exception as e:
                logger.warning(f"ffmpeg error at ts={ts}: {e}")

        return frame_map

    def replace_markers(
        self,
        markdown: str,
        frame_map: dict[int, Path],
        image_rel_path: str = "assets",
    ) -> str:
        """
        Replace Screenshot-[hh:mm:ss] markers with actual image references.

        Args:
            markdown: Markdown text with screenshot markers
            frame_map: Dict mapping timestamp -> image path
            image_rel_path: Relative path prefix for image references

        Returns:
            Markdown with markers replaced by image links
        """
        result = markdown

        markers = self.parse_markers(markdown)
        for marker, ts in markers:
            if ts in frame_map:
                img_name = frame_map[ts].name
                img_ref = f"![]({image_rel_path}/{img_name})"
                result = result.replace(marker, img_ref, 1)
                logger.info(f"Replaced marker {marker} with {img_ref}")
            else:
                logger.info(f"No frame for marker {marker}, keeping as-is")

        return result

    def copy_frames_to_vault(self, vault_assets_dir: Path) -> dict[int, Path]:
        """
        Copy extracted frames to the Obsidian vault assets directory.

        Returns:
            Updated frame_map with new paths in vault
        """
        vault_assets_dir = Path(vault_assets_dir)
        vault_assets_dir.mkdir(parents=True, exist_ok=True)

        new_map = {}
        for ts, src_path in {**getattr(self, '_frame_map', {})}.items():
            dest_path = vault_assets_dir / src_path.name
            shutil.copy2(src_path, dest_path)
            new_map[ts] = dest_path
            logger.info(f"Copied {src_path.name} to vault assets")

        return new_map

    def cleanup(self):
        """Remove temporary files."""
        if self._temp_dir and self._temp_dir.exists():
            try:
                shutil.rmtree(self._temp_dir)
                logger.info(f"Cleaned up temp dir: {self._temp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean up temp dir: {e}")
