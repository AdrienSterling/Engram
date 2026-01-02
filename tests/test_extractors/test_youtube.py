"""Tests for YouTube extractor."""

import pytest
from engram.extractors.youtube import YouTubeExtractor


class TestYouTubeExtractor:
    """Test YouTubeExtractor functionality."""

    @pytest.fixture
    def extractor(self):
        """Create extractor instance."""
        return YouTubeExtractor()

    def test_extract_video_id_standard(self, extractor):
        """Test video ID extraction from standard URL."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        video_id = extractor._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_short(self, extractor):
        """Test video ID extraction from short URL."""
        url = "https://youtu.be/dQw4w9WgXcQ"
        video_id = extractor._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_embed(self, extractor):
        """Test video ID extraction from embed URL."""
        url = "https://www.youtube.com/embed/dQw4w9WgXcQ"
        video_id = extractor._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_with_params(self, extractor):
        """Test video ID extraction with extra parameters."""
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=100&list=PLtest"
        video_id = extractor._extract_video_id(url)
        assert video_id == "dQw4w9WgXcQ"

    def test_extract_video_id_invalid(self, extractor):
        """Test video ID extraction from invalid URL."""
        url = "https://www.google.com"
        video_id = extractor._extract_video_id(url)
        assert video_id is None

    @pytest.mark.asyncio
    async def test_can_handle_youtube(self, extractor, sample_youtube_urls):
        """Test can_handle returns True for YouTube URLs."""
        for url in sample_youtube_urls:
            assert await extractor.can_handle(url) is True

    @pytest.mark.asyncio
    async def test_can_handle_non_youtube(self, extractor, sample_non_youtube_urls):
        """Test can_handle returns False for non-YouTube URLs."""
        for url in sample_non_youtube_urls:
            assert await extractor.can_handle(url) is False

    def test_combine_transcript(self, extractor):
        """Test transcript combination."""
        segments = [
            {"text": "Hello ", "start": 0, "duration": 1},
            {"text": "world!", "start": 1, "duration": 1},
            {"text": "  How are you?  ", "start": 2, "duration": 2},
        ]
        result = extractor._combine_transcript(segments)
        assert result == "Hello world! How are you?"

    # Integration test - requires network
    @pytest.mark.asyncio
    @pytest.mark.skip(reason="Integration test - requires network")
    async def test_extract_real_video(self, extractor):
        """Test extraction from a real video (integration test)."""
        # Use a video known to have transcripts
        url = "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
        result = await extractor.extract(url)

        assert result.title is not None
        assert len(result.content) > 0
        assert result.source_type.value == "youtube"
