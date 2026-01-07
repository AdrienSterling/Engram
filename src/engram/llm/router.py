"""LLM Router - manages multiple LLM providers and routing."""

import logging
from typing import Optional

from engram.core.config import Settings, get_settings
from engram.core.exceptions import ConfigError

from .base import BaseLLM
from .openai import OpenAILLM

logger = logging.getLogger(__name__)


class LLMRouter:
    """
    Manages multiple LLM providers and routes requests.

    Supports:
    - Multiple providers (OpenAI, Anthropic, DeepSeek)
    - Task-based routing (use cheaper models for simple tasks)
    - Fallback on failure
    """

    def __init__(self, settings: Optional[Settings] = None):
        """Initialize router with settings."""
        self.settings = settings or get_settings()
        self._providers: dict[str, BaseLLM] = {}
        self._initialize_providers()

    def _initialize_providers(self):
        """Initialize all configured LLM providers."""
        # OpenAI
        if self.settings.openai_api_key:
            self._providers["openai"] = OpenAILLM(
                api_key=self.settings.openai_api_key,
                model=self.settings.openai_model,
                base_url=self.settings.openai_base_url,
            )
            logger.info(f"Initialized OpenAI with model {self.settings.openai_model}")

        # DeepSeek (uses OpenAI-compatible API)
        if self.settings.deepseek_api_key:
            self._providers["deepseek"] = OpenAILLM(
                api_key=self.settings.deepseek_api_key,
                model=self.settings.deepseek_model,
                base_url=self.settings.deepseek_base_url,
            )
            logger.info(f"Initialized DeepSeek with model {self.settings.deepseek_model}")

        # Anthropic (placeholder - implement when needed)
        # if self.settings.anthropic_api_key:
        #     self._providers["anthropic"] = AnthropicLLM(...)

        if not self._providers:
            raise ConfigError("No LLM provider configured. Set at least one API key.")

        logger.info(f"Available LLM providers: {list(self._providers.keys())}")

    def get(self, provider: Optional[str] = None) -> BaseLLM:
        """
        Get LLM provider instance.

        Args:
            provider: Provider name. If None, use default.

        Returns:
            BaseLLM instance

        Raises:
            ConfigError if provider not available
        """
        provider = provider or self.settings.default_llm

        if provider not in self._providers:
            available = list(self._providers.keys())
            if available:
                # Fallback to first available
                provider = available[0]
                logger.warning(f"Provider not available, falling back to {provider}")
            else:
                raise ConfigError("No LLM provider available")

        return self._providers[provider]

    @property
    def default(self) -> BaseLLM:
        """Get default LLM provider."""
        return self.get()

    @property
    def available_providers(self) -> list[str]:
        """List available provider names."""
        return list(self._providers.keys())


# Global router instance
_router: Optional[LLMRouter] = None


def get_llm(provider: Optional[str] = None) -> BaseLLM:
    """
    Get LLM instance (convenience function).

    Args:
        provider: Optional provider name

    Returns:
        BaseLLM instance
    """
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router.get(provider)
