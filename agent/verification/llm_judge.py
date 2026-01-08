"""LLM-based code quality judgment."""

from typing import Dict, Any, List
from agent.llm.base import BaseLLMProvider
from agent.models import CodeChange


class LLMJudge:
    """Uses LLM to evaluate code quality and task completion."""

    def __init__(self, llm_provider: BaseLLMProvider):
        """
        Initialize LLM judge.

        Args:
            llm_provider: LLM provider for evaluation
        """
        self.llm_provider = llm_provider

    async def judge_completion(
        self,
        task_description: str,
        code_changes: List[CodeChange],
        test_output: str,
    ) -> Dict[str, Any]:
        """
        Judge whether task is complete and code quality is good.

        Args:
            task_description: Original task description
            code_changes: List of code changes made
            test_output: Output from test execution

        Returns:
            Dictionary with judgment results
        """
        # Prepare code summary
        code_summary = "\n\n".join(
            [
                f"File: {change.file_path}\nOperation: {change.operation}\n"
                + (f"Content:\n{change.content[:500]}..." if change.content else "")
                for change in code_changes
            ]
        )

        messages = [
            {
                "role": "system",
                "content": """You are a code review expert. Evaluate whether the code changes:
1. Complete the requested task
2. Follow best practices
3. Are well-tested
4. Have good code quality

Respond with JSON:
{
  "task_completed": true/false,
  "quality_score": 0.0-1.0,
  "issues": ["list", "of", "issues"],
  "suggestions": ["list", "of", "suggestions"],
  "reasoning": "explanation"
}""",
            },
            {
                "role": "user",
                "content": f"""Task: {task_description}

Code Changes:
{code_summary}

Test Output:
{test_output}

Evaluate the completion and quality:""",
            },
        ]

        try:
            schema = {
                "type": "object",
                "properties": {
                    "task_completed": {"type": "boolean"},
                    "quality_score": {"type": "number", "minimum": 0, "maximum": 1},
                    "issues": {"type": "array", "items": {"type": "string"}},
                    "suggestions": {"type": "array", "items": {"type": "string"}},
                    "reasoning": {"type": "string"},
                },
                "required": [
                    "task_completed",
                    "quality_score",
                    "issues",
                    "suggestions",
                ],
            }

            result = await self.llm_provider.generate_structured(
                messages, schema, temperature=0.3
            )

            return result

        except Exception as e:
            print(f"Warning: LLM judgment failed: {e}")
            # Fallback to simple judgment based on tests
            tests_passed = "passed" in test_output.lower() and "failed" not in test_output.lower()
            return {
                "task_completed": tests_passed,
                "quality_score": 0.7 if tests_passed else 0.3,
                "issues": ["LLM judgment unavailable"],
                "suggestions": [],
                "reasoning": f"Fallback judgment based on tests: {tests_passed}",
            }

    async def evaluate_code_quality(self, code: str, language: str) -> Dict[str, Any]:
        """
        Evaluate code quality for a specific code snippet.

        Args:
            code: Code to evaluate
            language: Programming language

        Returns:
            Dictionary with quality evaluation
        """
        messages = [
            {
                "role": "system",
                "content": f"You are a {language} code quality expert. Evaluate code for:\n"
                "1. Correctness\n"
                "2. Readability\n"
                "3. Performance\n"
                "4. Security\n"
                "5. Best practices\n\n"
                "Provide a score 0-1 and specific feedback.",
            },
            {
                "role": "user",
                "content": f"Evaluate this code:\n\n```{language}\n{code}\n```",
            },
        ]

        try:
            response = await self.llm_provider.generate(
                messages, temperature=0.3, max_tokens=1000
            )

            # Parse quality score from response
            content = response.content.lower()
            quality_score = 0.7  # Default

            # Try to extract numerical score
            import re

            score_match = re.search(r"score[:\s]+([0-9.]+)", content)
            if score_match:
                quality_score = float(score_match.group(1))
                if quality_score > 1:
                    quality_score = quality_score / 10  # Normalize if out of 10

            return {
                "quality_score": quality_score,
                "feedback": response.content,
            }

        except Exception as e:
            return {
                "quality_score": 0.5,
                "feedback": f"Evaluation failed: {e}",
            }

