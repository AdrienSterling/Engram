"""Extractor registry - manages available extractors."""

import logging
from typing import Optional

from engram.core.exceptions import ExtractorError

from .article import ArticleExtractor
from .base import BaseExtractor
from .youtube import YouTubeExtractor

logger = logging.getLogger(__name__)


class ExtractorRegistry:
    """
    Registry for content extractors.

    Automatically routes URLs to appropriate extractors.
    """

    def __init__(self):
        """Initialize registry with default extractors."""
        self._extractors: list[BaseExtractor] = []
        self._register_defaults()

    def _register_defaults(self):
        """Register default extractors."""
        # Order matters: more specific extractors first
        self.register(YouTubeExtractor())
        self.register(ArticleExtractor())  # General web articles (WeChat, etc.)
        # Future: PDFExtractor, ImageExtractor

    def register(self, extractor: BaseExtractor):
        """
        Register an extractor.

        Args:
            extractor: Extractor instance to register
        """
        self._extractors.append(extractor)
        logger.info(f"Registered extractor: {extractor.name}")

    async def get_extractor(self, url: str) -> Optional[BaseExtractor]:
        """
        Find extractor that can handle URL.

        Args:
            url: URL to check

        Returns:
            Matching extractor or None
        """
        for extractor in self._extractors:
            if await extractor.can_handle(url):
                logger.debug(f"URL matched extractor: {extractor.name}")
                return extractor
        return None

    async def extract(self, url: str):
        """
        Extract content from URL using appropriate extractor.

        Args:
            url: URL to extract from

        Returns:
            ExtractionResult

        Raises:
            ExtractorError if no extractor found or extraction fails
        """
        extractor = await self.get_extractor(url)
        if extractor is None:
            raise ExtractorError(f"No extractor found for URL: {url}")

        return await extractor.extract(url)


# Global registry instance
_registry: Optional[ExtractorRegistry] = None


def get_extractor(url: str) -> Optional[BaseExtractor]:
    """
    Get extractor for URL (convenience function).

    Args:
        url: URL to check

    Returns:
        Matching extractor or None
    """
    global _registry
    if _registry is None:
        _registry = ExtractorRegistry()
    # Note: This is sync wrapper, actual check is async
    # For proper use, call registry.get_extractor() directly
    return _registry
