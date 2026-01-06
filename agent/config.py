"""Configuration management for the coding agent."""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AgentConfig(BaseSettings):
    """Main configuration for the coding agent."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # OpenAI Configuration
    openai_api_key: str = Field(default="", description="OpenAI API key")
    openai_model: str = Field(default="gpt-4", description="OpenAI model name")
    openai_embedding_model: str = Field(
        default="text-embedding-3-small", description="OpenAI embedding model"
    )

    # Ollama Configuration
    ollama_base_url: str = Field(
        default="http://localhost:11434", description="Ollama server URL"
    )
    ollama_model: str = Field(default="llama3", description="Ollama model name")

    # Agent Configuration
    max_iterations: int = Field(default=10, description="Maximum agent loop iterations")
    context_window_size: int = Field(
        default=100000, description="Maximum context window size in tokens"
    )
    enable_sub_agents: bool = Field(
        default=True, description="Enable sub-agent dispatching"
    )

    # Vector Database Configuration
    chroma_persist_directory: str = Field(
        default="./data/chroma", description="ChromaDB persistence directory"
    )
    embedding_dimension: int = Field(
        default=1536, description="Embedding vector dimension"
    )

    # MCP Server Configuration
    mcp_filesystem_server: str = Field(
        default="stdio", description="Filesystem MCP server connection type"
    )
    mcp_playwright_server: str = Field(
        default="http://localhost:3000", description="Playwright MCP server URL"
    )

    # Logging Configuration
    log_level: str = Field(default="INFO", description="Logging level")
    log_file: str = Field(default="./logs/agent.log", description="Log file path")

    # Provider Selection
    default_llm_provider: str = Field(
        default="openai", description="Default LLM provider (openai or ollama)"
    )

    def validate_config(self) -> bool:
        """Validate the configuration."""
        if self.default_llm_provider == "openai" and not self.openai_api_key:
            raise ValueError("OpenAI API key is required when using OpenAI provider")
        return True


# Global config instance
_config: Optional[AgentConfig] = None


def get_config() -> AgentConfig:
    """Get the global configuration instance."""
    global _config
    if _config is None:
        _config = AgentConfig()
        _config.validate_config()
    return _config


def set_config(config: AgentConfig) -> None:
    """Set the global configuration instance."""
    global _config
    config.validate_config()
    _config = config

