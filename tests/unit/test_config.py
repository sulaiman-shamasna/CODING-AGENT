"""Unit tests for configuration."""

import pytest
from agent.config import AgentConfig


def test_default_config():
    """Test default configuration values."""
    config = AgentConfig()
    assert config.max_iterations == 10
    assert config.context_window_size == 100000
    assert config.default_llm_provider in ["openai", "ollama"]


def test_config_validation():
    """Test configuration validation."""
    config = AgentConfig(default_llm_provider="openai", openai_api_key="test_key")
    assert config.validate_config() is True


def test_invalid_provider():
    """Test invalid provider raises error."""
    from agent.llm.factory import create_llm_provider

    config = AgentConfig(default_llm_provider="invalid")
    with pytest.raises(ValueError):
        create_llm_provider(config)

