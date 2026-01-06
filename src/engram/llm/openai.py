"""OpenAI LLM implementation."""

import logging
from typing import Optional

from openai import AsyncOpenAI

from engram.core.types import Message, LLMResponse
from engram.core.exceptions import LLMError
from .base import BaseLLM

logger = logging.getLogger(__name__)


class OpenAILLM(BaseLLM):
    """OpenAI GPT implementation."""

    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4",
        base_url: Optional[str] = None,
    ):
        """
        Initialize OpenAI LLM.

        Args:
            api_key: OpenAI API key
            model: Model name (gpt-4, gpt-3.5-turbo, etc.)
            base_url: Optional custom base URL (for proxies)
        """
        self.model = model
        self.client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
        )

    async def chat(
        self,
        messages: list[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> LLMResponse:
        """Send chat messages to OpenAI."""
        try:
            # Convert to OpenAI format
            openai_messages = [{"role": msg.role, "content": msg.content} for msg in messages]

            response = await self.client.chat.completions.create(
                model=self.model,
                messages=openai_messages,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                raw_response=response,
            )

        except Exception as e:
            logger.error(f"OpenAI chat error: {e}")
            raise LLMError(f"OpenAI request failed: {e}") from e

    async def summarize(
        self,
        content: str,
        instruction: Optional[str] = None,
    ) -> str:
        """Summarize content using GPT."""
        if instruction:
            system_prompt = f"""你是一个内容提取助手。请根据用户的指令从内容中提取信息。

用户指令：{instruction}

请用中文回复，格式清晰，使用 Markdown。"""
        else:
            system_prompt = """你是一个内容总结助手。请总结以下内容的要点。

要求：
1. 提取 3-5 个关键要点
2. 每个要点一句话概括
3. 用中文回复
4. 使用 Markdown 格式"""

        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=content),
        ]

        response = await self.chat(messages, temperature=0.3)
        return response.content

    async def vision(
        self,
        image_url: str,
        prompt: str,
    ) -> LLMResponse:
        """Analyze image using GPT-4 Vision."""
        # Check if model supports vision
        if "vision" not in self.model and "gpt-4o" not in self.model:
            raise LLMError(f"Model {self.model} does not support vision")

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    }
                ],
                max_tokens=1000,
            )

            return LLMResponse(
                content=response.choices[0].message.content,
                model=response.model,
                usage={
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
                raw_response=response,
            )

        except Exception as e:
            logger.error(f"OpenAI vision error: {e}")
            raise LLMError(f"OpenAI vision request failed: {e}") from e
