"""Ollama LLM provider implementation."""

import json
from typing import Any, Dict, List, Optional
import ollama

from agent.llm.base import BaseLLMProvider, LLMResponse


class OllamaProvider(BaseLLMProvider):
    """Ollama LLM provider implementation."""

    def __init__(
        self,
        model_name: str = "llama3",
        base_url: str = "http://localhost:11434",
        **kwargs: Any,
    ):
        """Initialize Ollama provider."""
        super().__init__(model_name, **kwargs)
        self.base_url = base_url
        self.client = ollama.AsyncClient(host=base_url)

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text from messages using Ollama."""
        try:
            options = {"temperature": temperature}
            if max_tokens:
                options["num_predict"] = max_tokens

            response = await self.client.chat(
                model=self.model_name, messages=messages, options=options, **kwargs
            )

            content = response.get("message", {}).get("content", "")
            
            # Extract usage information if available
            usage = {}
            if "prompt_eval_count" in response:
                usage["prompt_tokens"] = response["prompt_eval_count"]
            if "eval_count" in response:
                usage["completion_tokens"] = response["eval_count"]
            if usage:
                usage["total_tokens"] = usage.get("prompt_tokens", 0) + usage.get(
                    "completion_tokens", 0
                )

            return LLMResponse(
                content=content,
                model=response.get("model", self.model_name),
                usage=usage,
                metadata={
                    "done": response.get("done", True),
                    "total_duration": response.get("total_duration", 0),
                },
            )

        except Exception as e:
            raise RuntimeError(f"Ollama API error: {str(e)}") from e

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """
        Generate structured output using Ollama.
        Note: Ollama doesn't have native function calling, so we use prompt engineering.
        """
        try:
            # Add schema to system message
            schema_prompt = f"\nYou must respond with valid JSON matching this schema:\n{json.dumps(schema, indent=2)}"
            
            # Modify the last message or add to system
            enhanced_messages = messages.copy()
            if enhanced_messages and enhanced_messages[-1]["role"] == "user":
                enhanced_messages[-1]["content"] += schema_prompt
            else:
                enhanced_messages.append({"role": "user", "content": schema_prompt})

            response = await self.generate(
                enhanced_messages, temperature=temperature, **kwargs
            )

            # Try to parse JSON from response
            content = response.content.strip()
            
            # Extract JSON if wrapped in markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            return json.loads(content)

        except json.JSONDecodeError as e:
            raise RuntimeError(
                f"Failed to parse structured output from Ollama: {str(e)}"
            ) from e
        except Exception as e:
            raise RuntimeError(f"Ollama structured generation error: {str(e)}") from e

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using Ollama."""
        try:
            embeddings = []
            for text in texts:
                response = await self.client.embeddings(model=self.model_name, prompt=text)
                embeddings.append(response.get("embedding", []))
            return embeddings

        except Exception as e:
            # Ollama might not support embeddings for all models
            raise RuntimeError(
                f"Ollama embedding error (model may not support embeddings): {str(e)}"
            ) from e

    def count_tokens(self, text: str) -> int:
        """
        Approximate token count for Ollama.
        Note: Different from tiktoken, this is an approximation.
        """
        # Rough approximation: 1 token ≈ 4 characters
        return len(text) // 4

