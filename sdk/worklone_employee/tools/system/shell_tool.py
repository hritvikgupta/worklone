"""
Shell Tool — run shell commands inside the workspace.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from worklone_employee.tools.base import BaseTool, ToolResult


class ShellTool(BaseTool):
    """Execute shell commands inside the workspace."""

    name = "run_shell"
    description = "Run a shell command in the workspace and return stdout, stderr, and exit code."
    category = "core"

    def get_schema(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Shell command to execute"},
                "cwd": {"type": "string", "description": "Optional working directory inside the workspace"},
                "timeout_seconds": {"type": "integer", "default": 30},
            },
            "required": ["command"],
        }

    async def execute(self, parameters: dict, context: dict = None) -> ToolResult:
        command = parameters.get("command", "")
        if not command:
            return ToolResult(False, "", error="command is required")

        root = Path((context or {}).get("workspace_root") or ".").resolve()
        cwd_value = parameters.get("cwd", "")
        cwd = (root / cwd_value).resolve() if cwd_value else root
        if cwd != root and root not in cwd.parents:
            return ToolResult(False, "", error="cwd must stay inside the workspace root")

        timeout_seconds = max(1, min(int(parameters.get("timeout_seconds", 30)), 300))

        try:
            result = subprocess.run(
                ["/bin/zsh", "-lc", command],
                cwd=str(cwd),
                capture_output=True,
                text=True,
                timeout=timeout_seconds,
            )
            output = (
                f"Exit code: {result.returncode}\n"
                f"STDOUT:\n{result.stdout[:12000] or '(empty)'}\n\n"
                f"STDERR:\n{result.stderr[:12000] or '(empty)'}"
            )
            return ToolResult(
                success=result.returncode == 0,
                output=output,
                error="" if result.returncode == 0 else result.stderr[:4000],
                data={"exit_code": result.returncode, "stdout": result.stdout, "stderr": result.stderr},
            )
        except subprocess.TimeoutExpired:
            return ToolResult(False, "", error=f"Command timed out after {timeout_seconds} seconds")
        except Exception as exc:
            return ToolResult(False, "", error=str(exc))
