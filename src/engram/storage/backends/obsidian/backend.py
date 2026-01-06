"""Obsidian storage backend implementation."""

import os
import subprocess
import logging
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path

from engram.core.types import Material, Idea, KnowledgeArea, InboxItem, DigestStatus
from engram.core.exceptions import StorageError
from engram.storage.base import BaseStorage
from .formatter import ObsidianFormatter

logger = logging.getLogger(__name__)


class ObsidianStorage(BaseStorage):
    """
    Obsidian storage backend.

    Stores content as Markdown files in an Obsidian vault,
    with optional Git synchronization.
    """

    name = "obsidian"

    def __init__(
        self,
        vault_path: str,
        git_enabled: bool = True,
        git_user_name: str = "Engram Bot",
        git_user_email: str = "bot@engram.local",
    ):
        """
        Initialize Obsidian storage.

        Args:
            vault_path: Path to Obsidian vault
            git_enabled: Whether to sync with Git
            git_user_name: Git commit author name
            git_user_email: Git commit author email
        """
        self.vault_path = Path(vault_path)
        self.git_enabled = git_enabled
        self.git_user_name = git_user_name
        self.git_user_email = git_user_email
        self.formatter = ObsidianFormatter()

        # Directory structure
        self.ideas_path = self.vault_path / "Ideas"
        self.knowledge_path = self.vault_path / "Knowledge"
        self.inbox_path = self.vault_path / "Inbox"

        # Ensure directories exist
        self._ensure_directories()

    def _ensure_directories(self):
        """Create directory structure if not exists."""
        dirs = [
            self.ideas_path / "1-种子",
            self.ideas_path / "2-验证中",
            self.knowledge_path,
            self.inbox_path,
        ]
        for dir_path in dirs:
            dir_path.mkdir(parents=True, exist_ok=True)

    async def _git_sync(self, file_path: Path, message: str):
        """Sync changes to Git."""
        if not self.git_enabled:
            return

        try:
            rel_path = file_path.relative_to(self.vault_path)
            vault = str(self.vault_path)

            # Use list arguments instead of shell string for cross-platform compatibility
            commands = [
                ["git", "-C", vault, "pull", "--rebase"],
                ["git", "-C", vault, "add", str(rel_path)],
                [
                    "git",
                    "-C",
                    vault,
                    "-c",
                    f"user.name={self.git_user_name}",
                    "-c",
                    f"user.email={self.git_user_email}",
                    "commit",
                    "-m",
                    message,
                ],
                ["git", "-C", vault, "push"],
            ]

            for cmd in commands:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                )
                if result.returncode != 0 and "nothing to commit" not in result.stdout:
                    logger.warning(f"Git command warning: {result.stderr}")

        except Exception as e:
            logger.error(f"Git sync error: {e}")
            # Don't raise - git sync failure shouldn't block storage

    async def _write_file(self, path: Path, content: str, git_message: str):
        """Write file and optionally sync to Git."""
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
            logger.info(f"Written file: {path}")

            await self._git_sync(path, git_message)

        except Exception as e:
            logger.error(f"Write file error: {e}")
            raise StorageError(f"Failed to write file: {e}") from e

    # ============ Ideas ============

    async def create_idea(self, idea: Idea) -> str:
        """Create a new idea file."""
        file_path = self.ideas_path / "1-种子" / f"{idea.title}.md"
        content = self.formatter.format_idea(idea)

        await self._write_file(file_path, content, f"Engram: 创建灵感 {idea.title}")

        return str(file_path)

    async def update_idea(self, idea_id: str, updates: dict) -> bool:
        """Update an existing idea."""
        # TODO: Implement idea update
        return True

    async def list_ideas(self, status: str = "active") -> list[Idea]:
        """List ideas from vault."""
        ideas = []
        search_paths = [
            self.ideas_path / "1-种子",
            self.ideas_path / "2-验证中",
        ]

        for search_path in search_paths:
            if not search_path.exists():
                continue

            for file_path in search_path.glob("*.md"):
                # Simple parsing - just get title from filename
                title = file_path.stem
                ideas.append(
                    Idea(
                        title=title,
                        summary="",
                        id=str(file_path),
                    )
                )

        return ideas

    async def add_material_to_idea(self, idea_id: str, material: Material) -> str:
        """Add material to an idea's materials folder."""
        idea_path = Path(idea_id)
        idea_dir = idea_path.parent / idea_path.stem

        # Create materials directory
        materials_dir = idea_dir / "materials"
        materials_dir.mkdir(parents=True, exist_ok=True)

        # Create material file
        date_str = material.captured_at.strftime("%Y-%m-%d")
        safe_title = self._safe_filename(material.title)
        file_path = materials_dir / f"{date_str}-{safe_title}.md"

        content = self.formatter.format_material(material)

        await self._write_file(file_path, content, f"Engram: 添加材料到 {idea_path.stem}")

        return str(file_path)

    # ============ Knowledge Areas ============

    async def create_knowledge_area(self, area: KnowledgeArea) -> str:
        """Create a new knowledge area."""
        area_dir = self.knowledge_path / area.title
        area_dir.mkdir(parents=True, exist_ok=True)

        # Create main file with underscore prefix
        file_path = area_dir / f"_{area.title}.md"
        content = self.formatter.format_knowledge_area(area)

        await self._write_file(file_path, content, f"Engram: 创建知识领域 {area.title}")

        # Create materials subdirectory
        (area_dir / "materials").mkdir(exist_ok=True)

        return str(file_path)

    async def list_knowledge_areas(self) -> list[KnowledgeArea]:
        """List all knowledge areas."""
        areas = []

        if not self.knowledge_path.exists():
            return areas

        for area_dir in self.knowledge_path.iterdir():
            if not area_dir.is_dir():
                continue

            # Look for main file
            main_file = area_dir / f"_{area_dir.name}.md"
            if main_file.exists():
                areas.append(
                    KnowledgeArea(
                        title=area_dir.name,
                        output_commitment="",  # TODO: Parse from file
                        id=str(main_file),
                    )
                )

        return areas

    async def add_material_to_knowledge(self, area_id: str, material: Material) -> str:
        """Add material to a knowledge area."""
        area_path = Path(area_id)
        area_dir = area_path.parent

        # Create material file in materials subdirectory
        materials_dir = area_dir / "materials"
        materials_dir.mkdir(exist_ok=True)

        date_str = material.captured_at.strftime("%Y-%m-%d")
        safe_title = self._safe_filename(material.title)
        file_path = materials_dir / f"{date_str}-{safe_title}.md"

        content = self.formatter.format_material(material)

        await self._write_file(file_path, content, f"Engram: 添加材料到知识领域 {area_dir.name}")

        return str(file_path)

    async def update_material_status(self, material_id: str, status: str) -> bool:
        """Update material digest status."""
        # TODO: Implement status update
        return True

    # ============ Inbox ============

    async def add_to_inbox(self, item: InboxItem) -> str:
        """Add item to temporary inbox."""
        inbox_file = self.inbox_path / "临时收集箱.md"

        # Read existing content or create new
        if inbox_file.exists():
            existing = inbox_file.read_text(encoding="utf-8")
        else:
            existing = self.formatter.format_inbox_header()

        # Append new item
        new_content = self.formatter.format_inbox_item(item)
        content = existing + "\n" + new_content

        await self._write_file(inbox_file, content, "Engram: 添加到临时收集箱")

        return str(inbox_file)

    async def save_to_inbox(self, filename: str, content: str) -> str:
        """
        Save a standalone file to the inbox folder.

        Args:
            filename: Name of the file (e.g., "20241230-Video-Summary.md")
            content: Full markdown content to save

        Returns:
            Path to the saved file
        """
        file_path = self.inbox_path / filename

        await self._write_file(file_path, content, f"Engram: 保存笔记 {filename}")

        return str(file_path)

    async def list_inbox(self, include_expired: bool = False) -> list[InboxItem]:
        """List inbox items."""
        # TODO: Parse inbox file and return items
        return []

    async def remove_from_inbox(self, item_id: str) -> bool:
        """Remove item from inbox."""
        # TODO: Implement removal
        return True

    # ============ Helpers ============

    def _safe_filename(self, name: str, max_length: int = 50) -> str:
        """Convert string to safe filename."""
        # Remove/replace unsafe characters
        unsafe = '<>:"/\\|?*'
        for char in unsafe:
            name = name.replace(char, "")

        # Truncate if too long
        if len(name) > max_length:
            name = name[:max_length]

        return name.strip()
