"""Test execution and result parsing."""

import asyncio
import re
from pathlib import Path
from typing import Optional
from agent.models import TestResult


class TestRunner:
    """Runs tests and parses results."""

    def __init__(self, workspace_path: str):
        """
        Initialize test runner.

        Args:
            workspace_path: Path to workspace
        """
        self.workspace_path = Path(workspace_path)

    async def run_tests(
        self,
        test_path: Optional[str] = None,
        framework: Optional[str] = None,
        timeout: int = 60,
    ) -> TestResult:
        """
        Run tests and parse results.

        Args:
            test_path: Specific test file/directory to run
            framework: Test framework (pytest, jest, etc.)
            timeout: Timeout in seconds

        Returns:
            TestResult object
        """
        # Detect framework if not specified
        if framework is None:
            framework = self._detect_framework()

        # Run tests based on framework
        if framework == "pytest":
            return await self._run_pytest(test_path, timeout)
        elif framework == "jest":
            return await self._run_jest(test_path, timeout)
        elif framework == "unittest":
            return await self._run_unittest(test_path, timeout)
        else:
            return TestResult(
                framework="unknown",
                output=f"Unsupported test framework: {framework}",
            )

    def _detect_framework(self) -> str:
        """Detect test framework from project files."""
        # Check for pytest
        if (self.workspace_path / "pytest.ini").exists() or (
            self.workspace_path / "pyproject.toml"
        ).exists():
            return "pytest"

        # Check for jest
        if (self.workspace_path / "jest.config.js").exists() or (
            self.workspace_path / "jest.config.ts"
        ).exists():
            return "jest"

        # Check for package.json with jest
        package_json = self.workspace_path / "package.json"
        if package_json.exists():
            try:
                import json

                with open(package_json) as f:
                    data = json.load(f)
                    if "jest" in data.get("devDependencies", {}):
                        return "jest"
            except Exception:
                pass

        # Default to pytest for Python projects
        if list(self.workspace_path.glob("**/*.py")):
            return "pytest"

        return "unknown"

    async def _run_pytest(
        self, test_path: Optional[str], timeout: int
    ) -> TestResult:
        """Run pytest tests."""
        cmd = ["pytest", "-v", "--tb=short"]
        if test_path:
            cmd.append(test_path)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_path),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            output = stdout.decode("utf-8", errors="ignore")
            error_output = stderr.decode("utf-8", errors="ignore")

            # Parse pytest output
            passed, failed, skipped = self._parse_pytest_output(output)
            error_messages = self._extract_error_messages(output)

            return TestResult(
                framework="pytest",
                passed=passed,
                failed=failed,
                skipped=skipped,
                output=output + "\n" + error_output,
                error_messages=error_messages,
            )

        except asyncio.TimeoutError:
            return TestResult(
                framework="pytest",
                output=f"Tests timed out after {timeout}s",
                error_messages=["Timeout"],
            )
        except Exception as e:
            return TestResult(
                framework="pytest",
                output=f"Error running tests: {e}",
                error_messages=[str(e)],
            )

    async def _run_jest(
        self, test_path: Optional[str], timeout: int
    ) -> TestResult:
        """Run jest tests."""
        cmd = ["npm", "test", "--", "--verbose"]
        if test_path:
            cmd.append(test_path)

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_path),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            output = stdout.decode("utf-8", errors="ignore")
            error_output = stderr.decode("utf-8", errors="ignore")

            # Parse jest output
            passed, failed, skipped = self._parse_jest_output(output)
            error_messages = self._extract_error_messages(output)

            return TestResult(
                framework="jest",
                passed=passed,
                failed=failed,
                skipped=skipped,
                output=output + "\n" + error_output,
                error_messages=error_messages,
            )

        except asyncio.TimeoutError:
            return TestResult(
                framework="jest",
                output=f"Tests timed out after {timeout}s",
                error_messages=["Timeout"],
            )
        except Exception as e:
            return TestResult(
                framework="jest",
                output=f"Error running tests: {e}",
                error_messages=[str(e)],
            )

    async def _run_unittest(
        self, test_path: Optional[str], timeout: int
    ) -> TestResult:
        """Run unittest tests."""
        cmd = ["python", "-m", "unittest", "discover"]
        if test_path:
            cmd.extend(["-s", test_path])

        try:
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.workspace_path),
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(), timeout=timeout
            )

            output = stdout.decode("utf-8", errors="ignore")
            error_output = stderr.decode("utf-8", errors="ignore")

            # Parse unittest output
            passed, failed, skipped = self._parse_unittest_output(
                output + error_output
            )
            error_messages = self._extract_error_messages(output + error_output)

            return TestResult(
                framework="unittest",
                passed=passed,
                failed=failed,
                skipped=skipped,
                output=output + "\n" + error_output,
                error_messages=error_messages,
            )

        except asyncio.TimeoutError:
            return TestResult(
                framework="unittest",
                output=f"Tests timed out after {timeout}s",
                error_messages=["Timeout"],
            )
        except Exception as e:
            return TestResult(
                framework="unittest",
                output=f"Error running tests: {e}",
                error_messages=[str(e)],
            )

    def _parse_pytest_output(self, output: str) -> tuple[int, int, int]:
        """Parse pytest output for test counts."""
        passed = failed = skipped = 0

        # Look for summary line like "5 passed, 2 failed, 1 skipped in 2.34s"
        match = re.search(
            r"(\d+)\s+passed|(\d+)\s+failed|(\d+)\s+skipped", output
        )
        if match:
            for line in output.split("\n"):
                if "passed" in line:
                    p_match = re.search(r"(\d+)\s+passed", line)
                    if p_match:
                        passed = int(p_match.group(1))
                if "failed" in line:
                    f_match = re.search(r"(\d+)\s+failed", line)
                    if f_match:
                        failed = int(f_match.group(1))
                if "skipped" in line:
                    s_match = re.search(r"(\d+)\s+skipped", line)
                    if s_match:
                        skipped = int(s_match.group(1))

        return passed, failed, skipped

    def _parse_jest_output(self, output: str) -> tuple[int, int, int]:
        """Parse jest output for test counts."""
        passed = failed = skipped = 0

        # Look for "Tests: 2 failed, 5 passed, 7 total"
        if "Tests:" in output:
            match = re.search(r"Tests:.*?(\d+)\s+passed", output)
            if match:
                passed = int(match.group(1))
            match = re.search(r"Tests:.*?(\d+)\s+failed", output)
            if match:
                failed = int(match.group(1))
            match = re.search(r"Tests:.*?(\d+)\s+skipped", output)
            if match:
                skipped = int(match.group(1))

        return passed, failed, skipped

    def _parse_unittest_output(self, output: str) -> tuple[int, int, int]:
        """Parse unittest output for test counts."""
        passed = failed = skipped = 0

        # Look for "Ran 10 tests in 0.234s"
        ran_match = re.search(r"Ran\s+(\d+)\s+test", output)
        if ran_match:
            total = int(ran_match.group(1))

            # Look for failures/errors
            fail_match = re.search(r"failures=(\d+)", output)
            error_match = re.search(r"errors=(\d+)", output)
            skip_match = re.search(r"skipped=(\d+)", output)

            failed = (
                int(fail_match.group(1)) if fail_match else 0
            ) + (int(error_match.group(1)) if error_match else 0)
            skipped = int(skip_match.group(1)) if skip_match else 0
            passed = total - failed - skipped

        return passed, failed, skipped

    def _extract_error_messages(self, output: str) -> list[str]:
        """Extract error messages from test output."""
        errors = []

        # Look for FAILED or ERROR lines
        for line in output.split("\n"):
            if "FAILED" in line or "ERROR" in line or "AssertionError" in line:
                errors.append(line.strip())

        return errors[:10]  # Limit to 10 errors

