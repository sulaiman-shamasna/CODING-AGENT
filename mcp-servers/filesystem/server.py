"""Filesystem MCP Server - provides file operations via MCP protocol."""

import os
import json
from pathlib import Path
from typing import Any, Dict, List, Optional
import asyncio


class FileSystemServer:
    """MCP server for filesystem operations."""

    def __init__(self, workspace_path: str):
        """Initialize filesystem server."""
        self.workspace_path = Path(workspace_path)
        self.tools = {
            "read_file": self.read_file,
            "write_file": self.write_file,
            "list_directory": self.list_directory,
            "search_files": self.search_files,
            "delete_file": self.delete_file,
        }

    async def read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Read file contents."""
        try:
            path = params.get("path")
            if not path:
                return {"error": "path parameter required"}

            file_path = self.workspace_path / path
            
            # Security check
            if not self._is_safe_path(file_path):
                return {"error": "Access denied: path outside workspace"}

            if not file_path.exists():
                return {"error": f"File not found: {path}"}

            with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()

            return {"content": content, "path": str(path)}

        except Exception as e:
            return {"error": str(e)}

    async def write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Write file contents."""
        try:
            path = params.get("path")
            content = params.get("content")

            if not path:
                return {"error": "path parameter required"}
            if content is None:
                return {"error": "content parameter required"}

            file_path = self.workspace_path / path

            # Security check
            if not self._is_safe_path(file_path):
                return {"error": "Access denied: path outside workspace"}

            # Create parent directories
            file_path.parent.mkdir(parents=True, exist_ok=True)

            with open(file_path, "w", encoding="utf-8") as f:
                f.write(content)

            return {"success": True, "path": str(path)}

        except Exception as e:
            return {"error": str(e)}

    async def list_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """List directory contents."""
        try:
            path = params.get("path", ".")
            dir_path = self.workspace_path / path

            # Security check
            if not self._is_safe_path(dir_path):
                return {"error": "Access denied: path outside workspace"}

            if not dir_path.exists():
                return {"error": f"Directory not found: {path}"}

            if not dir_path.is_dir():
                return {"error": f"Not a directory: {path}"}

            items = []
            for item in dir_path.iterdir():
                items.append(
                    {
                        "name": item.name,
                        "path": str(item.relative_to(self.workspace_path)),
                        "type": "directory" if item.is_dir() else "file",
                        "size": item.stat().st_size if item.is_file() else None,
                    }
                )

            return {"items": items, "path": str(path)}

        except Exception as e:
            return {"error": str(e)}

    async def search_files(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Search for files by pattern."""
        try:
            pattern = params.get("pattern")
            if not pattern:
                return {"error": "pattern parameter required"}

            max_results = params.get("max_results", 50)

            files = []
            for file_path in self.workspace_path.rglob(pattern):
                if file_path.is_file():
                    files.append(str(file_path.relative_to(self.workspace_path)))
                    if len(files) >= max_results:
                        break

            return {"files": files, "count": len(files)}

        except Exception as e:
            return {"error": str(e)}

    async def delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a file."""
        try:
            path = params.get("path")
            if not path:
                return {"error": "path parameter required"}

            file_path = self.workspace_path / path

            # Security check
            if not self._is_safe_path(file_path):
                return {"error": "Access denied: path outside workspace"}

            if not file_path.exists():
                return {"error": f"File not found: {path}"}

            file_path.unlink()

            return {"success": True, "path": str(path)}

        except Exception as e:
            return {"error": str(e)}

    def _is_safe_path(self, path: Path) -> bool:
        """Check if path is within workspace (security check)."""
        try:
            path.resolve().relative_to(self.workspace_path.resolve())
            return True
        except ValueError:
            return False

    async def handle_request(self, request: Dict[str, Any]) -> Dict[str, Any]:
        """Handle MCP request."""
        tool_name = request.get("tool")
        params = request.get("params", {})

        if tool_name not in self.tools:
            return {"error": f"Unknown tool: {tool_name}"}

        tool_func = self.tools[tool_name]
        return await tool_func(params)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        """Get tool schemas for MCP discovery."""
        return [
            {
                "name": "read_file",
                "description": "Read file contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"}
                    },
                    "required": ["path"],
                },
            },
            {
                "name": "write_file",
                "description": "Write file contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"},
                        "content": {"type": "string", "description": "File content"},
                    },
                    "required": ["path", "content"],
                },
            },
            {
                "name": "list_directory",
                "description": "List directory contents",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {
                            "type": "string",
                            "description": "Directory path (default: .)",
                        }
                    },
                },
            },
            {
                "name": "search_files",
                "description": "Search for files by pattern",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "pattern": {"type": "string", "description": "File pattern (e.g., *.py)"},
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum results",
                        },
                    },
                    "required": ["pattern"],
                },
            },
            {
                "name": "delete_file",
                "description": "Delete a file",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "path": {"type": "string", "description": "File path"}
                    },
                    "required": ["path"],
                },
            },
        ]


async def main():
    """Main entry point for stdio MCP server."""
    import sys

    workspace = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    server = FileSystemServer(workspace)

    # Simple stdio protocol
    while True:
        try:
            line = sys.stdin.readline()
            if not line:
                break

            request = json.loads(line)

            if request.get("method") == "tools/list":
                response = {"tools": server.get_tool_schemas()}
            else:
                response = await server.handle_request(request)

            print(json.dumps(response), flush=True)

        except Exception as e:
            print(json.dumps({"error": str(e)}), flush=True)


if __name__ == "__main__":
    asyncio.run(main())

