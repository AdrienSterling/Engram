"""Configuration management using Pydantic Settings."""

from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # === Telegram ===
    telegram_token: str

    # === Storage ===
    vault_path: str
    git_enabled: bool = True
    git_user_name: str = "Engram Bot"
    git_user_email: str = "bot@engram.local"

    # === LLM: OpenAI ===
    openai_api_key: Optional[str] = None
    openai_model: str = "gpt-4"
    openai_base_url: Optional[str] = None

    # === LLM: Anthropic ===
    anthropic_api_key: Optional[str] = None
    anthropic_model: str = "claude-3-sonnet-20240229"

    # === LLM: DeepSeek ===
    deepseek_api_key: Optional[str] = None
    deepseek_model: str = "deepseek-chat"
    deepseek_base_url: str = "https://api.deepseek.com/v1"

    # === Speech-to-Text: Groq Whisper ===
    groq_api_key: Optional[str] = None
    groq_whisper_model: str = "whisper-large-v3-turbo"

    # === General ===
    default_llm: str = "openai"
    log_level: str = "INFO"
    inbox_expiration_days: int = 7

    def get_available_llms(self) -> list[str]:
        """Return list of configured LLM providers."""
        available = []
        if self.openai_api_key:
            available.append("openai")
        if self.anthropic_api_key:
            available.append("anthropic")
        if self.deepseek_api_key:
            available.append("deepseek")
        return available


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
