"""Core type definitions."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Any


class SourceType(Enum):
    """Content source types."""

    YOUTUBE = "youtube"
    ARTICLE = "article"
    PDF = "pdf"
    IMAGE = "image"
    TEXT = "text"


class DigestStatus(Enum):
    """Knowledge digestion status."""

    UNREAD = "unread"
    READ = "read"
    INTERNALIZED = "internalized"
    OUTPUT = "output"

    @property
    def emoji(self) -> str:
        """Get emoji representation."""
        return {
            DigestStatus.UNREAD: "🔴",
            DigestStatus.READ: "🟡",
            DigestStatus.INTERNALIZED: "🟢",
            DigestStatus.OUTPUT: "⭐",
        }[self]

    @property
    def label(self) -> str:
        """Get Chinese label."""
        return {
            DigestStatus.UNREAD: "未读",
            DigestStatus.READ: "已读",
            DigestStatus.INTERNALIZED: "已内化",
            DigestStatus.OUTPUT: "已输出",
        }[self]


@dataclass
class Message:
    """Chat message for LLM."""

    role: str  # "system", "user", "assistant"
    content: str


@dataclass
class LLMResponse:
    """Response from LLM."""

    content: str
    model: str
    usage: dict = field(default_factory=dict)
    raw_response: Optional[Any] = None


@dataclass
class Material:
    """Extracted material/content."""

    title: str
    content: str
    source_type: SourceType
    source_url: Optional[str] = None
    user_query: Optional[str] = None

    # Metadata
    captured_at: datetime = field(default_factory=datetime.now)
    digest_status: DigestStatus = DigestStatus.UNREAD
    core_insight: Optional[str] = None

    # Assigned after storage
    id: Optional[str] = None


@dataclass
class Idea:
    """Idea/Project for "doing" path."""

    title: str
    summary: str
    status: str = "active"  # active, completed, archived

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    id: Optional[str] = None


@dataclass
class KnowledgeArea:
    """Knowledge area for "understanding" path."""

    title: str
    output_commitment: str  # What you commit to produce
    status: str = "active"

    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)

    id: Optional[str] = None


@dataclass
class InboxItem:
    """Temporary inbox item with expiration."""

    material: Material
    expires_at: datetime

    @property
    def is_expired(self) -> bool:
        """Check if item has expired."""
        return datetime.now() > self.expires_at
