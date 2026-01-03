"""OpenAI LLM provider implementation."""

import json
from typing import Any, Dict, List, Optional
import openai
from openai import AsyncOpenAI
import tiktoken

from agent.llm.base import BaseLLMProvider, LLMResponse


class OpenAIProvider(BaseLLMProvider):
    """OpenAI LLM provider implementation."""

    def __init__(
        self,
        api_key: str,
        model_name: str = "gpt-4",
        embedding_model: str = "text-embedding-3-small",
        **kwargs: Any,
    ):
        """Initialize OpenAI provider."""
        super().__init__(model_name, **kwargs)
        self.api_key = api_key
        self.embedding_model = embedding_model
        self.client = AsyncOpenAI(api_key=api_key)
        
        # Initialize tokenizer
        try:
            self.tokenizer = tiktoken.encoding_for_model(model_name)
        except KeyError:
            # Fallback to cl100k_base for unknown models
            self.tokenizer = tiktoken.get_encoding("cl100k_base")

    async def generate(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs: Any,
    ) -> LLMResponse:
        """Generate text from messages using OpenAI."""
        try:
            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs,
            )

            content = response.choices[0].message.content or ""
            usage = {
                "prompt_tokens": response.usage.prompt_tokens if response.usage else 0,
                "completion_tokens": response.usage.completion_tokens
                if response.usage
                else 0,
                "total_tokens": response.usage.total_tokens if response.usage else 0,
            }

            return LLMResponse(
                content=content,
                model=response.model,
                usage=usage,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "id": response.id,
                },
            )
        except Exception as e:
            raise RuntimeError(f"OpenAI API error: {str(e)}") from e

    async def generate_structured(
        self,
        messages: List[Dict[str, str]],
        schema: Dict[str, Any],
        temperature: float = 0.7,
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Generate structured output using OpenAI function calling."""
        try:
            # Use function calling for structured output
            functions = [
                {
                    "name": "structured_output",
                    "description": "Generate structured output",
                    "parameters": schema,
                }
            ]

            response = await self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                functions=functions,
                function_call={"name": "structured_output"},
                **kwargs,
            )

            function_call = response.choices[0].message.function_call
            if function_call and function_call.arguments:
                return json.loads(function_call.arguments)
            else:
                raise RuntimeError("No structured output generated")

        except Exception as e:
            raise RuntimeError(f"OpenAI structured generation error: {str(e)}") from e

    async def embed(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using OpenAI."""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model, input=texts
            )

            embeddings = [item.embedding for item in response.data]
            return embeddings

        except Exception as e:
            raise RuntimeError(f"OpenAI embedding error: {str(e)}") from e

    def count_tokens(self, text: str) -> int:
        """Count tokens using tiktoken."""
        try:
            tokens = self.tokenizer.encode(text)
            return len(tokens)
        except Exception:
            # Fallback to approximate count
            return len(text) // 4

