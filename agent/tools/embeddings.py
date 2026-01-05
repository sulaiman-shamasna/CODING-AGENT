"""Text embedding utilities."""

from typing import List
from agent.llm.base import BaseLLMProvider


class EmbeddingManager:
    """Manages text embeddings."""

    def __init__(self, llm_provider: BaseLLMProvider):
        """
        Initialize embedding manager.

        Args:
            llm_provider: LLM provider for generating embeddings
        """
        self.llm_provider = llm_provider

    async def embed_texts(self, texts: List[str], batch_size: int = 100) -> List[List[float]]:
        """
        Generate embeddings for texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Batch size for API calls

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            embeddings = await self.llm_provider.embed(batch)
            all_embeddings.extend(embeddings)

        return all_embeddings

    async def embed_single(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        embeddings = await self.llm_provider.embed([text])
        return embeddings[0] if embeddings else []

