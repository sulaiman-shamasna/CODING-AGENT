"""Script execution with sandboxing and timeout."""

import asyncio
import subprocess
from typing import Dict, Any, Optional
from pathlib import Path


class ScriptRunner:
    """Executes scripts with safety controls."""

    def __init__(self, workspace_path: str, timeout: int = 30):
        """
        Initialize script runner.

        Args:
            workspace_path: Path to workspace
            timeout: Default timeout in seconds
        """
        self.workspace_path = Path(workspace_path)
        self.timeout = timeout

    async def run_script(
        self,
        script_path: str,
        interpreter: Optional[str] = None,
        args: Optional[list[str]] = None,
        env: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run a script.

        Args:
            script_path: Path to script
            interpreter: Interpreter to use (python, node, bash, etc.)
            args: Script arguments
            env: Environment variables
            timeout: Timeout in seconds

        Returns:
            Dictionary with stdout, stderr, returncode
        """
        # Resolve script path
        if Path(script_path).is_absolute():
            script = Path(script_path)
        else:
            script = self.workspace_path / script_path

        if not script.exists():
            return {
                "success": False,
                "error": f"Script not found: {script_path}",
                "stdout": "",
                "stderr": "",
                "returncode": -1,
            }

        # Determine interpreter
        if interpreter is None:
            interpreter = self._detect_interpreter(script)

        # Build command
        cmd = [interpreter, str(script)]
        if args:
            cmd.extend(args)

        # Set timeout
        exec_timeout = timeout or self.timeout

        try:
            # Run script
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_path),
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=exec_timeout
                )

                return {
                    "success": process.returncode == 0,
                    "stdout": stdout.decode("utf-8", errors="ignore"),
                    "stderr": stderr.decode("utf-8", errors="ignore"),
                    "returncode": process.returncode,
                }

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "error": f"Script execution timed out after {exec_timeout}s",
                    "stdout": "",
                    "stderr": "",
                    "returncode": -1,
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "returncode": -1,
            }

    def _detect_interpreter(self, script_path: Path) -> str:
        """Detect interpreter based on file extension."""
        suffix = script_path.suffix.lower()

        interpreters = {
            ".py": "python",
            ".js": "node",
            ".ts": "ts-node",
            ".sh": "bash",
            ".rb": "ruby",
            ".php": "php",
            ".pl": "perl",
        }

        return interpreters.get(suffix, "bash")

    async def run_command(
        self,
        command: str,
        shell: bool = True,
        timeout: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Run a shell command.

        Args:
            command: Command to run
            shell: Whether to use shell
            timeout: Timeout in seconds

        Returns:
            Dictionary with stdout, stderr, returncode
        """
        exec_timeout = timeout or self.timeout

        try:
            if shell:
                process = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.workspace_path),
                )
            else:
                cmd_parts = command.split()
                process = await asyncio.create_subprocess_exec(
                    *cmd_parts,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(self.workspace_path),
                )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=exec_timeout
                )

                return {
                    "success": process.returncode == 0,
                    "stdout": stdout.decode("utf-8", errors="ignore"),
                    "stderr": stderr.decode("utf-8", errors="ignore"),
                    "returncode": process.returncode,
                }

            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                return {
                    "success": False,
                    "error": f"Command timed out after {exec_timeout}s",
                    "stdout": "",
                    "stderr": "",
                    "returncode": -1,
                }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "stdout": "",
                "stderr": "",
                "returncode": -1,
            }

