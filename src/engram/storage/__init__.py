"""Storage abstraction layer - supports multiple backends."""

from .backends.obsidian import ObsidianStorage
from .base import BaseStorage
from .factory import StorageFactory, get_storage

__all__ = [
    "BaseStorage",
    "ObsidianStorage",
    "StorageFactory",
    "get_storage",
]
