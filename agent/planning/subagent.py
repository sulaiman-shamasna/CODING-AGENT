"""Sub-agent system for specialized tasks."""

from typing import Any, Dict, Optional
from agent.models import SubAgentTask, Message
from agent.llm.base import BaseLLMProvider


class SubAgent:
    """A sub-agent with isolated context for specialized tasks."""

    def __init__(
        self,
        task: SubAgentTask,
        llm_provider: BaseLLMProvider,
        max_iterations: int = 5,
    ):
        """
        Initialize sub-agent.

        Args:
            task: Sub-agent task
            llm_provider: LLM provider
            max_iterations: Maximum iterations for sub-agent
        """
        self.task = task
        self.llm_provider = llm_provider
        self.max_iterations = max_iterations
        self.conversation_history: list[Message] = []

    async def execute(self) -> Dict[str, Any]:
        """
        Execute the sub-agent task.

        Returns:
            Task result
        """
        # Set up specialized system prompt based on specialization
        system_prompt = self._get_system_prompt()

        self.conversation_history = [
            Message(role="system", content=system_prompt),
            Message(
                role="user",
                content=f"Task: {self.task.description}\n\nContext: {self.task.context}",
            ),
        ]

        # Execute sub-agent loop
        for iteration in range(self.max_iterations):
            try:
                messages = [
                    {"role": msg.role, "content": msg.content}
                    for msg in self.conversation_history
                ]

                response = await self.llm_provider.generate(
                    messages, temperature=0.5, max_tokens=2000
                )

                # Add response to history
                self.conversation_history.append(
                    Message(role="assistant", content=response.content)
                )

                # Check if task is complete
                if self._is_task_complete(response.content):
                    return {
                        "status": "completed",
                        "result": response.content,
                        "iterations": iteration + 1,
                    }

            except Exception as e:
                return {
                    "status": "failed",
                    "error": str(e),
                    "iterations": iteration + 1,
                }

        return {
            "status": "max_iterations_reached",
            "result": self.conversation_history[-1].content
            if self.conversation_history
            else "",
            "iterations": self.max_iterations,
        }

    def _get_system_prompt(self) -> str:
        """Get specialized system prompt based on task type."""
        prompts = {
            "code_reviewer": """You are a specialized code review agent. Your task is to:
1. Analyze code for bugs, security issues, and performance problems
2. Check code style and best practices
3. Suggest improvements
4. Provide a detailed review report""",
            "test_generator": """You are a specialized test generation agent. Your task is to:
1. Analyze the code to understand its functionality
2. Generate comprehensive unit tests
3. Include edge cases and error scenarios
4. Follow testing best practices for the language""",
            "documentation_writer": """You are a specialized documentation agent. Your task is to:
1. Analyze code and understand its purpose
2. Write clear and comprehensive documentation
3. Include usage examples
4. Document parameters, return values, and exceptions""",
            "refactoring_specialist": """You are a specialized refactoring agent. Your task is to:
1. Analyze code for refactoring opportunities
2. Suggest design pattern improvements
3. Improve code maintainability and readability
4. Preserve functionality while improving structure""",
        }

        return prompts.get(
            self.task.specialization,
            "You are a helpful coding assistant focused on completing the given task.",
        )

    def _is_task_complete(self, response: str) -> bool:
        """Check if the task is complete based on response."""
        # Simple completion check - can be made more sophisticated
        completion_indicators = [
            "task complete",
            "finished",
            "done",
            "completed successfully",
        ]
        response_lower = response.lower()
        return any(indicator in response_lower for indicator in completion_indicators)


class SubAgentDispatcher:
    """Dispatches and manages sub-agents."""

    def __init__(self, llm_provider: BaseLLMProvider):
        """
        Initialize sub-agent dispatcher.

        Args:
            llm_provider: LLM provider for sub-agents
        """
        self.llm_provider = llm_provider
        self.active_subagents: Dict[str, SubAgent] = {}

    async def dispatch(self, task: SubAgentTask) -> Dict[str, Any]:
        """
        Dispatch a sub-agent for a task.

        Args:
            task: Sub-agent task

        Returns:
            Task result
        """
        # Create and execute sub-agent
        subagent = SubAgent(
            task=task, llm_provider=self.llm_provider, max_iterations=5
        )

        self.active_subagents[task.id] = subagent

        result = await subagent.execute()

        # Store result in task
        task.result = result

        # Clean up
        del self.active_subagents[task.id]

        return result

    def get_active_count(self) -> int:
        """Get number of active sub-agents."""
        return len(self.active_subagents)

