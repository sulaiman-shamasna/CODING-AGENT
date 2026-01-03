"""Base LLM provider interface."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel


class LLMResponse(BaseModel):
    """Response from LLM generation."""

    content: str
    model: str
    usage: Dict[str, int] = {}
    metadata: Dict[str, Any] = {}


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, model_name: str, **kwargs: Any):
        """Initialize the provider."""
        self.model_name = model_name
        self.kwargs = kwargs

    @abstractmethod
    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate text from messages.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional provider-specific parameters

        Returns:
            LLMResponse object
        """
        pass

    @abstractmethod
    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate structured output conforming to a schema.

        Args:
            messages: List of message dictionaries
            schema: JSON schema for structured output
            temperature: Sampling temperature
            **kwargs: Additional parameters

        Returns:
            Dictionary conforming to the schema
        """
        pass

    @abstractmethod
    async def embed(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        pass

    @abstractmethod
    def count_tokens(self, text: str) -> int:
        """
        Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        pass

    async def generate_with_retry(
        self,
        messages: List[Dict[str, str]],
        max_retries: int = 3,
        **kwargs: Any,
    ) -> LLMResponse:
        """
        Generate with retry logic.

        Args:
            messages: List of message dictionaries
            max_retries: Maximum number of retries
            **kwargs: Additional parameters

        Returns:
            LLMResponse object
        """
        import asyncio

        for attempt in range(max_retries):
            try:
                return await self.generate(messages, **kwargs)
            except Exception as e:
                if attempt == max_retries - 1:
                    raise
                wait_time = 2**attempt  # Exponential backoff
                await asyncio.sleep(wait_time)
        raise RuntimeError("Max retries exceeded")

