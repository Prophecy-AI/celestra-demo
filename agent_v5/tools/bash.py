"""
Bash tool for executing shell commands
"""
import asyncio
import uuid
import time
from typing import Dict, Optional
from .base import BaseTool
from .bash_process_registry import BackgroundProcess, BashProcessRegistry


class BashTool(BaseTool):
    """Execute shell commands in workspace directory"""

    def __init__(self, workspace_dir: str, process_registry: Optional[BashProcessRegistry] = None):
        """
        Initialize Bash tool

        Args:
            workspace_dir: Directory where commands execute
            process_registry: Optional registry for background process tracking
        """
        super().__init__(workspace_dir)
        self.process_registry = process_registry

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def schema(self) -> Dict:
        return {
            "name": "Bash",
            "description": "Execute shell commands in the workspace directory. Set background=true to run long-running commands (like model training) without blocking - you can then use ReadBashOutput to monitor progress. IMPORTANT: Stay within the workspace directory - do not use '..' or absolute paths to access files outside your workspace.",
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
                        "description": "Timeout in milliseconds (max 600000, only applies to foreground execution)",
                        "default": 120000
                    },
                    "background": {
                        "type": "boolean",
                        "description": "REQUIRED: Explicitly choose execution mode. If true, run command in background and return shell_id immediately. Use ReadBashOutput(shell_id) to monitor progress and KillShell(shell_id) to stop it. Perfect for long-running tasks like model training. If false, command blocks until completion (max 120s timeout)."
                    }
                },
                "required": ["command", "background"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        """Execute command in foreground or background based on input params"""
        command = input["command"]
        background = input.get("background", False)

        if background:
            return await self._execute_background(command)
        else:
            timeout_ms = input.get("timeout", 120000)
            timeout_s = min(timeout_ms / 1000, 600)
            return await self._execute_foreground(command, timeout_s)

    async def _execute_foreground(self, command: str, timeout_s: float) -> Dict:
        """Execute command in foreground (blocking until completion)"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_dir  # Use cwd parameter, not cd &&
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_s
            )

            output = stdout.decode() + stderr.decode()
            exit_code = process.returncode

            # Truncate output for display
            if len(output) > 30000:
                output = output[:30000] + "\n... (output truncated)"

            # Truncate debug_summary too (prevent massive strings in logs)
            debug_output = output.replace('\n', ' | ')
            if len(debug_output) > 200:
                debug_output = debug_output[:200] + "..."

            return {
                "content": output,
                "is_error": False,
                "debug_summary": f"exit {exit_code}: {debug_output}"
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

    async def _execute_background(self, command: str) -> Dict:
        """Execute command in background, return shell_id immediately"""
        if self.process_registry is None:
            return {
                "content": "Background execution not available: no process registry configured.\n"
                          "To use background execution, the agent must be initialized with a BashProcessRegistry.",
                "is_error": True
            }

        shell_id = f"bash_{uuid.uuid4().hex[:8]}"

        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.workspace_dir  # Use cwd parameter, not cd &&
            )

            # Create background process object
            bg_process = BackgroundProcess(
                process=process,
                command=command,
                start_time=time.time()
            )

            # Register in registry
            self.process_registry.register(shell_id, bg_process)

            # Start background task to collect output and store reference
            collector_task = asyncio.create_task(self._collect_output(shell_id))
            bg_process.collector_task = collector_task

            return {
                "content": (
                    f"Started background process: {shell_id}\n"
                    f"Command: {command}\n\n"
                    f"Use ReadBashOutput(shell_id='{shell_id}') to monitor progress.\n"
                    f"Use KillShell(shell_id='{shell_id}') to stop it if needed."
                ),
                "is_error": False,
                "debug_summary": f"started {shell_id}"
            }

        except Exception as e:
            return {
                "content": f"Failed to start background process: {str(e)}",
                "is_error": True
            }

    async def _collect_output(self, shell_id: str) -> None:
        """
        Background task: collect stdout/stderr from process streams incrementally

        Uses non-blocking reads with small timeouts to capture output as it arrives.
        Runs until process completes. Handles process being killed gracefully.
        """
        if self.process_registry is None:
            return

        bg_process = self.process_registry.get(shell_id)
        if not bg_process:
            return

        try:
            async def read_stdout():
                """Read stdout stream with non-blocking incremental reads"""
                if bg_process.process.stdout:
                    while bg_process.process.returncode is None:
                        try:
                            # Non-blocking read with timeout
                            chunk = await asyncio.wait_for(
                                bg_process.process.stdout.read(1024),
                                timeout=0.1
                            )
                            if chunk:
                                bg_process.append_stdout(chunk)
                        except asyncio.TimeoutError:
                            # No data yet, sleep briefly and retry
                            await asyncio.sleep(0.05)

                    # Drain any remaining output after process exits
                    remaining = await bg_process.process.stdout.read()
                    if remaining:
                        bg_process.append_stdout(remaining)

            async def read_stderr():
                """Read stderr stream with non-blocking incremental reads"""
                if bg_process.process.stderr:
                    while bg_process.process.returncode is None:
                        try:
                            chunk = await asyncio.wait_for(
                                bg_process.process.stderr.read(1024),
                                timeout=0.1
                            )
                            if chunk:
                                bg_process.append_stderr(chunk)
                        except asyncio.TimeoutError:
                            await asyncio.sleep(0.05)

                    # Drain remaining
                    remaining = await bg_process.process.stderr.read()
                    if remaining:
                        bg_process.append_stderr(remaining)

            # Read both streams concurrently
            await asyncio.gather(read_stdout(), read_stderr())

            # Wait for process to complete
            await bg_process.process.wait()

        except Exception:
            # Process might be killed externally, that's fine
            pass
