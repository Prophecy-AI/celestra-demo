"""
Registry for managing background bash processes

Each agent instance has its own registry (dependency injection pattern).
Background processes accumulate stdout/stderr in memory with configurable limits.
"""
import asyncio
import time
from typing import Dict, Optional
from dataclasses import dataclass, field


# Max bytes to store per stream (10MB default) - prevents memory exhaustion
DEFAULT_MAX_BUFFER_SIZE = 10 * 1024 * 1024


@dataclass
class BackgroundProcess:
    """Represents a running background bash process with output buffering"""

    process: asyncio.subprocess.Process
    command: str
    start_time: float

    # Output buffers (grow as process produces output)
    stdout_data: bytearray = field(default_factory=bytearray)
    stderr_data: bytearray = field(default_factory=bytearray)

    # Read cursors (track what's been read by ReadBashOutput)
    stdout_cursor: int = 0
    stderr_cursor: int = 0

    # Memory limit per stream
    max_buffer_size: int = DEFAULT_MAX_BUFFER_SIZE

    # Collector task (for cleanup)
    collector_task: Optional[asyncio.Task] = None

    def append_stdout(self, data: bytes) -> None:
        """Append stdout data, enforcing max buffer size"""
        self.stdout_data.extend(data)

        # Drop old data if over limit (keep most recent)
        if len(self.stdout_data) > self.max_buffer_size:
            overflow = len(self.stdout_data) - self.max_buffer_size
            self.stdout_data = self.stdout_data[overflow:]
            # Adjust cursor (data before cursor was dropped)
            self.stdout_cursor = max(0, self.stdout_cursor - overflow)

    def append_stderr(self, data: bytes) -> None:
        """Append stderr data, enforcing max buffer size"""
        self.stderr_data.extend(data)

        if len(self.stderr_data) > self.max_buffer_size:
            overflow = len(self.stderr_data) - self.max_buffer_size
            self.stderr_data = self.stderr_data[overflow:]
            self.stderr_cursor = max(0, self.stderr_cursor - overflow)


class BashProcessRegistry:
    """
    Registry for managing background bash processes

    Each agent instance gets its own registry (DI pattern).
    Tracks running processes and their accumulated output.
    """

    def __init__(self):
        self._processes: Dict[str, BackgroundProcess] = {}

    def register(self, shell_id: str, process: BackgroundProcess) -> None:
        """Register a new background process"""
        self._processes[shell_id] = process

    def get(self, shell_id: str) -> Optional[BackgroundProcess]:
        """Get process by shell_id, returns None if not found"""
        return self._processes.get(shell_id)

    def remove(self, shell_id: str) -> None:
        """Remove process from registry (call after kill or completion)"""
        self._processes.pop(shell_id, None)

    def list_all(self) -> Dict[str, BackgroundProcess]:
        """Get all processes (returns copy for safe iteration)"""
        return self._processes.copy()

    async def cleanup(self) -> int:
        """
        Kill all running processes, cancel collector tasks, and clear registry

        Returns:
            Number of processes killed
        """
        killed_count = 0

        for shell_id, bg_process in self.list_all().items():
            # Kill process if still running
            if bg_process.process.returncode is None:
                try:
                    bg_process.process.kill()
                    await bg_process.process.wait()
                    killed_count += 1
                except Exception:
                    pass  # Process might have already exited

            # Cancel collector task if running
            if bg_process.collector_task and not bg_process.collector_task.done():
                bg_process.collector_task.cancel()
                try:
                    await bg_process.collector_task
                except asyncio.CancelledError:
                    pass  # Expected

        self._processes.clear()
        return killed_count

    def reset(self) -> None:
        """
        Clear registry without killing processes (for testing only)

        WARNING: This orphans background processes. Only use in tests.
        """
        self._processes.clear()
