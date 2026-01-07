"""Base extractor interface."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional

from engram.core.types import SourceType


@dataclass
class ExtractionResult:
    """Result from content extraction."""

    title: str
    content: str
    source_type: SourceType
    source_url: str

    # Optional metadata
    author: Optional[str] = None
    duration: Optional[int] = None  # seconds for video
    language: Optional[str] = None
    extracted_at: datetime = field(default_factory=datetime.now)

    # Raw data for debugging
    raw_data: Optional[dict] = None


class BaseExtractor(ABC):
    """
    Abstract base class for content extractors.

    Each extractor handles a specific content type (YouTube, web, PDF, etc.)
    """

    name: str
    source_type: SourceType

    @abstractmethod
    async def can_handle(self, url: str) -> bool:
        """
        Check if this extractor can handle the given URL.

        Args:
            url: URL to check

        Returns:
            True if this extractor can handle the URL
        """
        pass

    @abstractmethod
    async def extract(self, url: str) -> ExtractionResult:
        """
        Extract content from URL.

        Args:
            url: URL to extract from

        Returns:
            ExtractionResult with extracted content

        Raises:
            ExtractorError on failure
        """
        pass
