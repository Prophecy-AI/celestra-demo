"""
Read incremental output from background bash process
"""
from typing import Dict, Optional
from .base import BaseTool
from .bash_process_registry import BashProcessRegistry


class ReadBashOutputTool(BaseTool):
    """Read new output from background bash process (cursor-based incremental reading)"""

    def __init__(self, workspace_dir: str, process_registry: Optional[BashProcessRegistry] = None):
        """
        Initialize ReadBashOutput tool

        Args:
            workspace_dir: Workspace directory (required by BaseTool but not used)
            process_registry: Registry to query for background processes
        """
        super().__init__(workspace_dir)
        self.process_registry = process_registry

    @property
    def name(self) -> str:
        return "ReadBashOutput"

    @property
    def schema(self) -> Dict:
        return {
            "name": "ReadBashOutput",
            "description": (
                "Read new output from a background bash process. Returns only NEW output "
                "since the last read (cursor-based incremental reading). Use this to monitor "
                "long-running commands like model training. Call periodically to see progress. "
                "Each call advances the cursor, so you never see the same output twice."
            ),
            "input_schema": {
                "type": "object",
                "properties": {
                    "shell_id": {
                        "type": "string",
                        "description": "Shell ID from background Bash execution (e.g., 'bash_a1b2c3d4')"
                    }
                },
                "required": ["shell_id"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        """Read incremental output from background process"""
        if self.process_registry is None:
            return {
                "content": (
                    "ReadBashOutput not available: no process registry configured.\n"
                    "Background execution requires a BashProcessRegistry."
                ),
                "is_error": True
            }

        shell_id = input["shell_id"]
        bg_process = self.process_registry.get(shell_id)

        if not bg_process:
            return {
                "content": (
                    f"Shell {shell_id} not found.\n\n"
                    f"Possible reasons:\n"
                    f"- Shell ID is incorrect\n"
                    f"- Process was already killed with KillShell\n"
                    f"- Process completed and was cleaned up\n\n"
                    f"Use Bash(background=true) to start a new background process."
                ),
                "is_error": True
            }

        # Get NEW output only (from cursor to current end)
        new_stdout = bg_process.stdout_data[bg_process.stdout_cursor:].decode('utf-8', errors='replace')
        new_stderr = bg_process.stderr_data[bg_process.stderr_cursor:].decode('utf-8', errors='replace')

        # Combine stdout and stderr (preserve chronological order as much as possible)
        # Note: Perfect chronological ordering isn't possible with separate streams
        new_output = new_stdout + new_stderr

        # Update cursors (mark this output as read)
        bg_process.stdout_cursor = len(bg_process.stdout_data)
        bg_process.stderr_cursor = len(bg_process.stderr_data)

        # Check process status
        if bg_process.process.returncode is not None:
            status = f"COMPLETED (exit code: {bg_process.process.returncode})"
        else:
            status = "RUNNING"

        # Calculate runtime
        import time
        runtime_s = time.time() - bg_process.start_time

        # Format output
        if new_output.strip():
            content = (
                f"[{status}] {shell_id} (runtime: {runtime_s:.1f}s)\n"
                f"Command: {bg_process.command}\n\n"
                f"{new_output}"
            )
            debug_summary = f"{status}, {len(new_output)} new bytes"
        else:
            content = (
                f"[{status}] {shell_id} (runtime: {runtime_s:.1f}s)\n"
                f"Command: {bg_process.command}\n\n"
                f"(no new output since last read)"
            )
            debug_summary = f"{status}, no new output"

        return {
            "content": content,
            "is_error": False,
            "debug_summary": debug_summary
        }
