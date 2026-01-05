"""File operation utilities."""

import os
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime


class FileOperations:
    """File operation utilities with backup support."""

    def __init__(self, workspace_path: str, backup_dir: str = "./backups"):
        """
        Initialize file operations.

        Args:
            workspace_path: Path to the workspace
            backup_dir: Directory for backups
        """
        self.workspace_path = Path(workspace_path)
        self.backup_dir = Path(backup_dir)
        self.backup_dir.mkdir(parents=True, exist_ok=True)

    def read_file(self, file_path: str) -> str:
        """Read file contents."""
        target = self.workspace_path / file_path
        with open(target, "r", encoding="utf-8") as f:
            return f.read()

    def write_file(self, file_path: str, content: str, create_backup: bool = True) -> None:
        """
        Write content to file.

        Args:
            file_path: Path to file
            content: Content to write
            create_backup: Whether to create backup if file exists
        """
        target = self.workspace_path / file_path

        # Create backup if file exists
        if target.exists() and create_backup:
            self._backup_file(target)

        # Create parent directories if needed
        target.parent.mkdir(parents=True, exist_ok=True)

        # Write file
        with open(target, "w", encoding="utf-8") as f:
            f.write(content)

    def delete_file(self, file_path: str, create_backup: bool = True) -> None:
        """
        Delete file.

        Args:
            file_path: Path to file
            create_backup: Whether to create backup before deletion
        """
        target = self.workspace_path / file_path

        if not target.exists():
            return

        if create_backup:
            self._backup_file(target)

        target.unlink()

    def _backup_file(self, file_path: Path) -> None:
        """Create backup of file."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.name}.{timestamp}.bak"
        backup_path = self.backup_dir / backup_name

        shutil.copy2(file_path, backup_path)

    def generate_diff(self, file_path: str, new_content: str) -> str:
        """
        Generate diff between current file and new content.

        Args:
            file_path: Path to file
            new_content: New content

        Returns:
            Diff string
        """
        import difflib

        target = self.workspace_path / file_path

        if target.exists():
            old_content = self.read_file(file_path)
            old_lines = old_content.splitlines(keepends=True)
            new_lines = new_content.splitlines(keepends=True)

            diff = difflib.unified_diff(
                old_lines, new_lines, fromfile=f"a/{file_path}", tofile=f"b/{file_path}"
            )
            return "".join(diff)
        else:
            return f"New file: {file_path}\n{new_content}"

