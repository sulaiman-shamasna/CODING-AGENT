"""Context window management for the agent."""

from typing import List, Dict, Any
from agent.models import Message
from agent.llm.base import BaseLLMProvider


class ContextManager:
    """Manages context window to prevent overflow."""

    def __init__(
        self, llm_provider: BaseLLMProvider, max_context_size: int = 100000
    ):
        """
        Initialize context manager.

        Args:
            llm_provider: LLM provider for token counting and summarization
            max_context_size: Maximum context window size in tokens
        """
        self.llm_provider = llm_provider
        self.max_context_size = max_context_size
        self.conversation_history: List[Message] = []

    def add_message(self, message: Message) -> None:
        """Add a message to the conversation history."""
        self.conversation_history.append(message)

    def get_current_size(self) -> int:
        """Get current context size in tokens."""
        total_tokens = 0
        for message in self.conversation_history:
            total_tokens += self.llm_provider.count_tokens(message.content)
        return total_tokens

    def should_compact(self) -> bool:
        """Check if context should be compacted."""
        return self.get_current_size() > self.max_context_size * 0.8  # 80% threshold

    async def compact_context(self, keep_recent: int = 5) -> None:
        """
        Compact context by summarizing older messages.

        Args:
            keep_recent: Number of recent messages to keep unchanged
        """
        if len(self.conversation_history) <= keep_recent:
            return

        # Keep system messages and recent messages
        system_messages = [
            msg for msg in self.conversation_history if msg.role == "system"
        ]
        recent_messages = self.conversation_history[-keep_recent:]
        messages_to_summarize = self.conversation_history[
            len(system_messages) : -keep_recent
        ]

        if not messages_to_summarize:
            return

        # Create summary
        summary_prompt = [
            {
                "role": "system",
                "content": "You are a helpful assistant that summarizes conversations concisely while preserving important information.",
            },
            {
                "role": "user",
                "content": f"Summarize this conversation, preserving key decisions, code changes, and important context:\n\n"
                + "\n\n".join(
                    [
                        f"{msg.role}: {msg.content}"
                        for msg in messages_to_summarize
                    ]
                ),
            },
        ]

        try:
            response = await self.llm_provider.generate(
                summary_prompt, temperature=0.3, max_tokens=1000
            )

            summary_message = Message(
                role="system",
                content=f"[Summary of previous conversation]: {response.content}",
                metadata={"type": "summary"},
            )

            # Rebuild conversation history
            self.conversation_history = (
                system_messages + [summary_message] + recent_messages
            )

        except Exception as e:
            # If summarization fails, just remove old messages
            print(f"Warning: Context summarization failed: {e}")
            self.conversation_history = system_messages + recent_messages

    def get_messages(self) -> List[Dict[str, str]]:
        """Get messages in LLM API format."""
        return [
            {"role": msg.role, "content": msg.content}
            for msg in self.conversation_history
        ]

    def clear(self) -> None:
        """Clear conversation history."""
        self.conversation_history = []

