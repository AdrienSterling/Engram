"""Tests for Obsidian storage backend."""

from pathlib import Path

import pytest

from engram.core.types import Idea, KnowledgeArea, Material, SourceType
from engram.storage.backends.obsidian import ObsidianStorage


class TestObsidianStorage:
    """Test ObsidianStorage functionality."""

    @pytest.fixture
    def storage(self, temp_vault):
        """Create storage instance with temp vault."""
        return ObsidianStorage(
            vault_path=str(temp_vault),
            git_enabled=False,  # Disable git for tests
        )

    @pytest.mark.asyncio
    async def test_create_idea(self, storage, temp_vault):
        """Test idea creation."""
        idea = Idea(
            title="测试灵感",
            summary="这是一个测试灵感",
        )

        path = await storage.create_idea(idea)

        assert Path(path).exists()
        content = Path(path).read_text(encoding="utf-8")
        assert "测试灵感" in content
        assert "这是一个测试灵感" in content

    @pytest.mark.asyncio
    async def test_list_ideas(self, storage, temp_vault):
        """Test listing ideas."""
        # Create a test idea
        idea = Idea(title="列表测试", summary="测试")
        await storage.create_idea(idea)

        ideas = await storage.list_ideas()

        assert len(ideas) >= 1
        assert any(i.title == "列表测试" for i in ideas)

    @pytest.mark.asyncio
    async def test_create_knowledge_area(self, storage, temp_vault):
        """Test knowledge area creation."""
        area = KnowledgeArea(
            title="大模型",
            output_commitment="写一篇入门文章",
        )

        path = await storage.create_knowledge_area(area)

        assert Path(path).exists()
        content = Path(path).read_text(encoding="utf-8")
        assert "大模型" in content
        assert "写一篇入门文章" in content

    @pytest.mark.asyncio
    async def test_add_material_to_idea(self, storage, temp_vault):
        """Test adding material to an idea."""
        # First create an idea
        idea = Idea(title="材料测试", summary="测试")
        idea_path = await storage.create_idea(idea)

        # Add material
        material = Material(
            title="测试视频",
            content="这是测试内容",
            source_type=SourceType.YOUTUBE,
            source_url="https://youtube.com/watch?v=test",
        )

        material_path = await storage.add_material_to_idea(idea_path, material)

        assert Path(material_path).exists()
        content = Path(material_path).read_text(encoding="utf-8")
        assert "测试视频" in content
        assert "测试内容" in content

    def test_safe_filename(self, storage):
        """Test safe filename generation."""
        # Test with unsafe characters
        unsafe = 'Test: File/Name<>|"?*'
        safe = storage._safe_filename(unsafe)
        assert ":" not in safe
        assert "/" not in safe
        assert "<" not in safe

        # Test truncation
        long_name = "a" * 100
        truncated = storage._safe_filename(long_name, max_length=50)
        assert len(truncated) <= 50
