"""Code generation and application."""

from typing import List, Optional, Dict, Any
from agent.models import CodeChange
from agent.llm.base import BaseLLMProvider
from agent.tools.file_ops import FileOperations


class CodeGenerator:
    """Generates and applies code changes."""

    def __init__(
        self, llm_provider: BaseLLMProvider, file_ops: FileOperations
    ):
        """
        Initialize code generator.

        Args:
            llm_provider: LLM provider for code generation
            file_ops: File operations utility
        """
        self.llm_provider = llm_provider
        self.file_ops = file_ops

    async def generate_code(
        self,
        task_description: str,
        context: Optional[str] = None,
        language: Optional[str] = None,
    ) -> str:
        """
        Generate code based on task description.

        Args:
            task_description: Description of what code should do
            context: Additional context (existing code, requirements)
            language: Programming language

        Returns:
            Generated code
        """
        messages = [
            {
                "role": "system",
                "content": "You are an expert programmer. Generate clean, well-documented code.",
            },
            {
                "role": "user",
                "content": f"Task: {task_description}\n\n"
                + (f"Language: {language}\n\n" if language else "")
                + (f"Context: {context}\n\n" if context else "")
                + "Generate the code:",
            },
        ]

        response = await self.llm_provider.generate(
            messages, temperature=0.3, max_tokens=2000
        )

        return self._extract_code(response.content)

    async def generate_code_changes(
        self,
        plan: str,
        existing_files: Dict[str, str],
    ) -> List[CodeChange]:
        """
        Generate code changes based on plan.

        Args:
            plan: Execution plan
            existing_files: Dictionary of file_path -> content

        Returns:
            List of code changes
        """
        messages = [
            {
                "role": "system",
                "content": """You are a code generation assistant. Given a plan and existing code, 
generate the necessary changes. For each change, specify:
1. file_path: Path to the file
2. operation: create, update, or delete
3. content: New file content (for create/update)

Output in JSON format:
{"changes": [{"file_path": "...", "operation": "...", "content": "..."}]}""",
            },
            {
                "role": "user",
                "content": f"Plan: {plan}\n\nExisting files:\n"
                + "\n".join([f"{path}:\n{content[:500]}" for path, content in existing_files.items()])
                + "\n\nGenerate changes:",
            },
        ]

        try:
            schema = {
                "type": "object",
                "properties": {
                    "changes": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "file_path": {"type": "string"},
                                "operation": {
                                    "type": "string",
                                    "enum": ["create", "update", "delete"],
                                },
                                "content": {"type": "string"},
                            },
                            "required": ["file_path", "operation"],
                        },
                    }
                },
                "required": ["changes"],
            }

            result = await self.llm_provider.generate_structured(
                messages, schema, temperature=0.3
            )

            changes = []
            for change_dict in result.get("changes", []):
                change = CodeChange(
                    file_path=change_dict["file_path"],
                    operation=change_dict["operation"],
                    content=change_dict.get("content"),
                )
                changes.append(change)

            return changes

        except Exception as e:
            print(f"Warning: Failed to generate structured changes: {e}")
            return []

    def apply_changes(
        self, changes: List[CodeChange], preview: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Apply code changes to files.

        Args:
            changes: List of code changes
            preview: If True, only generate diffs without applying

        Returns:
            List of results for each change
        """
        results = []

        for change in changes:
            try:
                if preview:
                    # Generate diff only
                    if change.operation in ["create", "update"] and change.content:
                        diff = self.file_ops.generate_diff(
                            change.file_path, change.content
                        )
                        change.diff = diff
                        results.append(
                            {
                                "file_path": change.file_path,
                                "operation": change.operation,
                                "success": True,
                                "diff": diff,
                            }
                        )
                    else:
                        results.append(
                            {
                                "file_path": change.file_path,
                                "operation": change.operation,
                                "success": True,
                                "message": f"Will {change.operation} file",
                            }
                        )
                else:
                    # Apply change
                    if change.operation == "create" or change.operation == "update":
                        if not change.content:
                            raise ValueError("Content required for create/update")
                        self.file_ops.write_file(change.file_path, change.content)
                        results.append(
                            {
                                "file_path": change.file_path,
                                "operation": change.operation,
                                "success": True,
                            }
                        )
                    elif change.operation == "delete":
                        self.file_ops.delete_file(change.file_path)
                        results.append(
                            {
                                "file_path": change.file_path,
                                "operation": "delete",
                                "success": True,
                            }
                        )

            except Exception as e:
                results.append(
                    {
                        "file_path": change.file_path,
                        "operation": change.operation,
                        "success": False,
                        "error": str(e),
                    }
                )

        return results

    def _extract_code(self, response: str) -> str:
        """Extract code from LLM response (removing markdown formatting)."""
        lines = response.split("\n")
        code_lines = []
        in_code_block = False

        for line in lines:
            if line.strip().startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or (not line.strip().startswith("#") and line.strip()):
                code_lines.append(line)

        return "\n".join(code_lines)

