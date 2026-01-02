"""Base LLM interface - all providers implement this."""

from abc import ABC, abstractmethod
from typing import Optional

from engram.core.types import Message, LLMResponse


class BaseLLM(ABC):
    """
    Abstract base class for LLM providers.

    All LLM implementations (OpenAI, Anthropic, DeepSeek, etc.)
    must implement this interface.
    """

    name: str  # Provider name: "openai", "anthropic", "deepseek"

    @abstractmethod
    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """
        Send chat messages and get response.

        Args:
            messages: List of chat messages
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens in response

        Returns:
            LLMResponse with content and metadata
        """
        pass

    @abstractmethod
    async def summarize(
        self,
        content: str,
        instruction: Optional[str] = None,
    ) -> str:
        """
        Summarize content with optional custom instruction.

        Args:
            content: Text content to summarize
            instruction: Custom extraction/summary instruction

        Returns:
            Summary text
        """
        pass

    async def vision(
        self,
        image_url: str,
        prompt: str,
    ) -> LLMResponse:
        """
        Analyze image (for multimodal models).

        Args:
            image_url: URL or base64 of image
            prompt: Analysis prompt

        Returns:
            LLMResponse with analysis

        Raises:
            NotImplementedError if model doesn't support vision
        """
        raise NotImplementedError(f"{self.name} does not support vision")
