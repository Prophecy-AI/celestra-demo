"""
Bash tool for executing shell commands
"""
import asyncio
from typing import Dict
from .base import BaseTool


class BashTool(BaseTool):
    """Execute shell commands in workspace directory"""

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def schema(self) -> Dict:
        return {
            "name": "Bash",
            "description": "Execute shell commands in the workspace directory. IMPORTANT: Stay within the workspace directory - do not use '..' or absolute paths to access files outside your workspace.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    },
                    "description": {
                        "type": "string",
                        "description": "Human-readable description of what this command does"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in milliseconds (max 600000)",
                        "default": 120000
                    }
                },
                "required": ["command"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        command = input["command"]
        timeout_ms = input.get("timeout", 120000)
        timeout_s = min(timeout_ms / 1000, 600)

        try:
            process = await asyncio.create_subprocess_shell(
                f"cd {self.workspace_dir} && {command}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_s
            )

            output = stdout.decode() + stderr.decode()
            exit_code = process.returncode

            if len(output) > 30000:
                output = output[:30000] + "\n... (output truncated)"

            return {
                "content": output,
                "is_error": False,
                "debug_summary": f"exit {exit_code}: {output[:80].replace(chr(10), ' | ')}"
            }

        except asyncio.TimeoutError:
            return {
                "content": f"Command timed out after {timeout_s}s",
                "is_error": True
            }
        except Exception as e:
            return {
                "content": f"Error executing command: {str(e)}",
                "is_error": True
            }
