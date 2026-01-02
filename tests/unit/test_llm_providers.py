"""Unit tests for LLM providers."""

import pytest
from unittest.mock import AsyncMock, patch
from agent.llm.openai_provider import OpenAIProvider
from agent.llm.ollama_provider import OllamaProvider


@pytest.mark.asyncio
async def test_openai_token_counting():
    """Test OpenAI token counting."""
    provider = OpenAIProvider(api_key="test_key", model_name="gpt-4")
    count = provider.count_tokens("Hello world")
    assert count > 0
    assert isinstance(count, int)


@pytest.mark.asyncio
async def test_ollama_token_counting():
    """Test Ollama token counting."""
    provider = OllamaProvider(model_name="llama3")
    count = provider.count_tokens("Hello world")
    assert count > 0
    assert isinstance(count, int)

