"""Shell-based search tools for codebase exploration."""

import os
import subprocess
from typing import List, Optional
from pathlib import Path
from agent.models import SearchResult


class ShellSearch:
    """Shell-based search tools using standard Unix commands."""

    def __init__(self, workspace_path: str):
        """
        Initialize shell search.

        Args:
            workspace_path: Path to the workspace/codebase
        """
        self.workspace_path = Path(workspace_path)

    def search_files(
        self, pattern: str, max_results: int = 50
    ) -> List[SearchResult]:
        """
        Search for files by name pattern.

        Args:
            pattern: File name pattern (supports wildcards)
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        try:
            # Use find command
            cmd = ["find", str(self.workspace_path), "-name", pattern, "-type", "f"]
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(self.workspace_path),
            )

            files = result.stdout.strip().split("\n")
            files = [f for f in files if f][:max_results]

            return [
                SearchResult(
                    source=file,
                    content=f"File: {file}",
                    relevance_score=1.0,
                    metadata={"search_type": "filename"},
                )
                for file in files
            ]

        except Exception as e:
            print(f"Warning: File search failed: {e}")
            return []

    def grep_content(
        self, pattern: str, file_pattern: str = "*", max_results: int = 50
    ) -> List[SearchResult]:
        """
        Search file contents using grep.

        Args:
            pattern: Content pattern to search for
            file_pattern: File pattern to limit search
            max_results: Maximum number of results

        Returns:
            List of search results
        """
        try:
            # Try ripgrep if available, fallback to grep
            rg_available = (
                subprocess.run(
                    ["which", "rg"], capture_output=True, timeout=1
                ).returncode
                == 0
            )

            if rg_available:
                cmd = [
                    "rg",
                    "--max-count",
                    "5",
                    "--context",
                    "2",
                    "--line-number",
                    pattern,
                    str(self.workspace_path),
                ]
            else:
                cmd = [
                    "grep",
                    "-r",
                    "-n",
                    "-i",
                    "-m",
                    "5",
                    pattern,
                    str(self.workspace_path),
                ]

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=10
            )

            lines = result.stdout.strip().split("\n")
            lines = [line for line in lines if line][:max_results]

            results = []
            for line in lines:
                if ":" in line:
                    parts = line.split(":", 2)
                    if len(parts) >= 2:
                        file_path = parts[0]
                        content = parts[-1] if len(parts) > 2 else parts[1]
                        results.append(
                            SearchResult(
                                source=file_path,
                                content=content.strip(),
                                relevance_score=0.8,
                                metadata={"search_type": "grep", "pattern": pattern},
                            )
                        )

            return results

        except Exception as e:
            print(f"Warning: Content search failed: {e}")
            return []

    def list_directory(
        self, relative_path: str = ".", max_depth: int = 2
    ) -> List[str]:
        """
        List directory contents.

        Args:
            relative_path: Path relative to workspace
            max_depth: Maximum depth to traverse

        Returns:
            List of file/directory paths
        """
        try:
            target_path = self.workspace_path / relative_path

            if not target_path.exists():
                return []

            # Use find with maxdepth
            cmd = [
                "find",
                str(target_path),
                "-maxdepth",
                str(max_depth),
                "-type",
                "f",
            ]
            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=5
            )

            files = result.stdout.strip().split("\n")
            return [f for f in files if f]

        except Exception as e:
            print(f"Warning: Directory listing failed: {e}")
            return []

    def read_file(self, file_path: str, max_lines: Optional[int] = None) -> str:
        """
        Read file contents.

        Args:
            file_path: Path to file (relative or absolute)
            max_lines: Maximum number of lines to read

        Returns:
            File contents as string
        """
        try:
            # Resolve path
            if Path(file_path).is_absolute():
                target = Path(file_path)
            else:
                target = self.workspace_path / file_path

            if not target.exists():
                return f"File not found: {file_path}"

            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                if max_lines:
                    lines = [next(f) for _ in range(max_lines)]
                    content = "".join(lines)
                else:
                    content = f.read()

            return content

        except Exception as e:
            return f"Error reading file: {e}"

