"""Storage abstraction layer - supports multiple backends."""

from .base import BaseStorage
from .backends.obsidian import ObsidianStorage
from .factory import StorageFactory, get_storage

__all__ = [
    "BaseStorage",
    "ObsidianStorage",
    "StorageFactory",
    "get_storage",
]
