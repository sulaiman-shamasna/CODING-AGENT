"""LLM provider factory."""

from typing import Optional
from agent.config import AgentConfig
from agent.llm.base import BaseLLMProvider
from agent.llm.openai_provider import OpenAIProvider
from agent.llm.ollama_provider import OllamaProvider


def create_llm_provider(
    config: AgentConfig, provider_type: Optional[str] = None
) -> BaseLLMProvider:
    """
    Create an LLM provider based on configuration.

    Args:
        config: Agent configuration
        provider_type: Override provider type (openai or ollama)

    Returns:
        BaseLLMProvider instance
    """
    provider = provider_type or config.default_llm_provider

    if provider == "openai":
        return OpenAIProvider(
            api_key=config.openai_api_key,
            model_name=config.openai_model,
            embedding_model=config.openai_embedding_model,
        )
    elif provider == "ollama":
        return OllamaProvider(
            model_name=config.ollama_model, base_url=config.ollama_base_url
        )
    else:
        raise ValueError(f"Unknown LLM provider: {provider}")

