"""Base storage interface - all backends implement this."""

from abc import ABC, abstractmethod
from typing import Optional

from engram.core.types import Material, Idea, KnowledgeArea, InboxItem


class BaseStorage(ABC):
    """
    Abstract base class for storage backends.

    All storage implementations (Obsidian, Notion, Google Docs, etc.)
    must implement this interface.
    """

    name: str  # Backend name: "obsidian", "notion", "google_docs"

    # ============ Ideas/Projects ============

    @abstractmethod
    async def create_idea(self, idea: Idea) -> str:
        """
        Create a new idea/project.

        Args:
            idea: Idea to create

        Returns:
            ID/path of created idea
        """
        pass

    @abstractmethod
    async def update_idea(self, idea_id: str, updates: dict) -> bool:
        """
        Update an existing idea.

        Args:
            idea_id: ID of idea to update
            updates: Dictionary of fields to update

        Returns:
            True if successful
        """
        pass

    @abstractmethod
    async def list_ideas(self, status: str = "active") -> list[Idea]:
        """
        List ideas filtered by status.

        Args:
            status: Filter by status (active, completed, archived)

        Returns:
            List of ideas
        """
        pass

    @abstractmethod
    async def add_material_to_idea(self, idea_id: str, material: Material) -> str:
        """
        Add material to an idea.

        Args:
            idea_id: Target idea ID
            material: Material to add

        Returns:
            ID/path of created material file
        """
        pass

    # ============ Knowledge Areas ============

    @abstractmethod
    async def create_knowledge_area(self, area: KnowledgeArea) -> str:
        """
        Create a new knowledge area.

        Args:
            area: Knowledge area to create

        Returns:
            ID/path of created area
        """
        pass

    @abstractmethod
    async def list_knowledge_areas(self) -> list[KnowledgeArea]:
        """
        List all knowledge areas.

        Returns:
            List of knowledge areas
        """
        pass

    @abstractmethod
    async def add_material_to_knowledge(
        self, area_id: str, material: Material
    ) -> str:
        """
        Add material to a knowledge area.

        Args:
            area_id: Target knowledge area ID
            material: Material to add

        Returns:
            ID/path of created material file
        """
        pass

    @abstractmethod
    async def update_material_status(
        self, material_id: str, status: str
    ) -> bool:
        """
        Update material digest status.

        Args:
            material_id: Material ID
            status: New status

        Returns:
            True if successful
        """
        pass

    # ============ Inbox ============

    @abstractmethod
    async def add_to_inbox(self, item: InboxItem) -> str:
        """
        Add item to temporary inbox.

        Args:
            item: Inbox item with expiration

        Returns:
            ID of created item
        """
        pass

    @abstractmethod
    async def list_inbox(self, include_expired: bool = False) -> list[InboxItem]:
        """
        List inbox items.

        Args:
            include_expired: Whether to include expired items

        Returns:
            List of inbox items
        """
        pass

    @abstractmethod
    async def remove_from_inbox(self, item_id: str) -> bool:
        """
        Remove item from inbox.

        Args:
            item_id: Item to remove

        Returns:
            True if successful
        """
        pass

    # ============ Search ============

    async def search(self, query: str, scope: str = "all") -> list[dict]:
        """
        Search across content.

        Args:
            query: Search query
            scope: Search scope (all, ideas, knowledge, inbox)

        Returns:
            List of matching items
        """
        # Default implementation - can be overridden
        return []
