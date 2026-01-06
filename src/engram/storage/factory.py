"""Storage factory - creates storage backend instances."""

import logging
from typing import Optional, Type

from engram.core.config import Settings, get_settings
from engram.core.exceptions import ConfigError
from .base import BaseStorage
from .backends.obsidian import ObsidianStorage

logger = logging.getLogger(__name__)


class StorageFactory:
    """
    Factory for creating storage backend instances.

    Supports registration of custom backends for extensibility.
    """

    _backends: dict[str, Type[BaseStorage]] = {
        "obsidian": ObsidianStorage,
        # "notion": NotionStorage,  # Future
        # "google_docs": GoogleDocsStorage,  # Future
    }

    @classmethod
    def create(
        cls,
        backend_type: str = "obsidian",
        settings: Optional[Settings] = None,
        **kwargs,
    ) -> BaseStorage:
        """
        Create a storage backend instance.

        Args:
            backend_type: Type of backend (obsidian, notion, etc.)
            settings: Optional settings override
            **kwargs: Additional backend-specific arguments

        Returns:
            BaseStorage instance

        Raises:
            ConfigError if backend type unknown
        """
        if backend_type not in cls._backends:
            available = list(cls._backends.keys())
            raise ConfigError(
                f"Unknown storage backend: {backend_type}. " f"Available: {available}"
            )

        settings = settings or get_settings()
        backend_class = cls._backends[backend_type]

        # Build kwargs based on backend type
        if backend_type == "obsidian":
            backend_kwargs = {
                "vault_path": settings.vault_path,
                "git_enabled": settings.git_enabled,
                "git_user_name": settings.git_user_name,
                "git_user_email": settings.git_user_email,
                **kwargs,
            }
        else:
            backend_kwargs = kwargs

        logger.info(f"Creating {backend_type} storage backend")
        return backend_class(**backend_kwargs)

    @classmethod
    def register(cls, name: str, backend_class: Type[BaseStorage]):
        """
        Register a new storage backend.

        Allows third-party extensions to add custom backends.

        Args:
            name: Backend name
            backend_class: Class implementing BaseStorage
        """
        cls._backends[name] = backend_class
        logger.info(f"Registered storage backend: {name}")

    @classmethod
    def available_backends(cls) -> list[str]:
        """List available backend names."""
        return list(cls._backends.keys())


# Global storage instance
_storage: Optional[BaseStorage] = None


def get_storage(backend_type: str = "obsidian") -> BaseStorage:
    """
    Get storage instance (convenience function).

    Args:
        backend_type: Type of backend

    Returns:
        BaseStorage instance
    """
    global _storage
    if _storage is None:
        _storage = StorageFactory.create(backend_type)
    return _storage
