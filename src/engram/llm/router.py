"""LLM Router - manages multiple LLM providers and routing."""

import logging
from typing import Optional

import aiohttp

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
                provider_name="deepseek",
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

    async def diagnostic(self) -> str:
        """Run diagnostic tests on all configured LLM providers."""
        lines = ["🔍 LLM 诊断报告", ""]
        settings = self.settings

        for name, llm in self._providers.items():
            provider = getattr(llm, "name", name)
            model = getattr(llm, "model", "?")
            base_url = str(getattr(llm.client, "base_url", "?"))
            lines.append(f"*{provider}* ({model})")
            lines.append(f"  URL: {base_url}")

            try:
                response = await llm.chat(
                    [type("Message", (), {"role": "user", "content": "hi"})()],
                    temperature=0,
                    max_tokens=10,
                )
                lines.append(f"  ✅ 连接正常 (tokens: {response.usage.get('total_tokens', '?')})")
            except Exception as e:
                lines.append(f"  ❌ 连接失败: {str(e)[:200]}")

            if name == "deepseek":
                try:
                    key = mask_key(settings.deepseek_api_key or "")
                    api_url = "https://api.deepseek.com/user/balance"
                    async with aiohttp.ClientSession() as session:
                        async with session.get(
                            api_url,
                            headers={"Authorization": f"Bearer {settings.deepseek_api_key}"},
                            timeout=aiohttp.ClientTimeout(total=10),
                        ) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                balance = data.get("balance_infos", [{}])[0]
                                lines.append(f"  💰 余额: {balance.get('total_balance', '?')} {balance.get('currency', '')}")
                            else:
                                text = await resp.text()
                                lines.append(f"  💰 余额查询失败: HTTP {resp.status} {text[:100]}")
                except Exception as e:
                    lines.append(f"  💰 余额查询异常: {str(e)[:100]}")

            lines.append("")

        lines.append(f"默认 LLM: {settings.default_llm}")
        return "\n".join(lines)


def mask_key(key: str) -> str:
    """Mask API key for display."""
    if len(key) <= 8:
        return "***"
    return key[:4] + "****" + key[-4:]


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


async def run_diagnostic() -> str:
    """Run LLM diagnostic and return report string."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return await _router.diagnostic()
