"""Pytest configuration and fixtures."""

import os
import pytest
from pathlib import Path


@pytest.fixture
def temp_vault(tmp_path):
    """Create a temporary vault directory for testing."""
    vault = tmp_path / "test_vault"
    vault.mkdir()

    # Create basic structure
    (vault / "Ideas" / "1-种子").mkdir(parents=True)
    (vault / "Ideas" / "2-验证中").mkdir(parents=True)
    (vault / "Knowledge").mkdir()
    (vault / "Inbox").mkdir()

    return vault


@pytest.fixture
def mock_env(monkeypatch, temp_vault):
    """Set up mock environment variables."""
    monkeypatch.setenv("TELEGRAM_TOKEN", "test_token")
    monkeypatch.setenv("VAULT_PATH", str(temp_vault))
    monkeypatch.setenv("OPENAI_API_KEY", "test_key")
    monkeypatch.setenv("GIT_ENABLED", "false")


@pytest.fixture
def sample_youtube_urls():
    """Sample YouTube URLs for testing."""
    return [
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        "https://youtu.be/dQw4w9WgXcQ",
        "https://www.youtube.com/embed/dQw4w9WgXcQ",
        "https://youtube.com/watch?v=dQw4w9WgXcQ&t=100",
    ]


@pytest.fixture
def sample_non_youtube_urls():
    """Sample non-YouTube URLs for testing."""
    return [
        "https://www.google.com",
        "https://github.com/user/repo",
        "https://example.com/video.mp4",
    ]
