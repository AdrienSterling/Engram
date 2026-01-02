"""Custom exceptions for Engram."""


class EngramError(Exception):
    """Base exception for Engram."""

    pass


class LLMError(EngramError):
    """LLM-related errors."""

    pass


class ExtractorError(EngramError):
    """Content extraction errors."""

    pass


class StorageError(EngramError):
    """Storage-related errors."""

    pass


class ConfigError(EngramError):
    """Configuration errors."""

    pass
