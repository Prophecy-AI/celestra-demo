"""
IO handler abstraction for CLI and WebSocket modes
"""
from abc import ABC, abstractmethod
from typing import Optional, Any
import sys


class IOHandler(ABC):
    """Abstract base class for IO handling"""

    @abstractmethod
    def send_output(self, message: str) -> None:
        """Send output message to user"""
        pass

    @abstractmethod
    def get_user_input(self, prompt: str = "") -> str:
        """Get input from user"""
        pass

    @abstractmethod
    def send_log(self, message: str, level: str = "info") -> None:
        """Send debug log (only when DEBUG=1)"""
        pass


class CLIHandler(IOHandler):
    """Standard CLI IO handler using stdin/stdout"""

    def send_output(self, message: str) -> None:
        print(message)
        sys.stdout.flush()

    def get_user_input(self, prompt: str = "") -> str:
        return input(prompt)

    def send_log(self, message: str, level: str = "info") -> None:
        # Logs go to stdout in CLI mode (controlled by DEBUG env)
        pass  # Logging is handled by existing tool_log function


class WebSocketHandler(IOHandler):
    """WebSocket IO handler for remote clients"""

    def __init__(self, websocket: Any, receive_queue: Any):
        self.websocket = websocket
        self.receive_queue = receive_queue

    async def send_output(self, message: str) -> None:
        """Send output to WebSocket client"""
        import json
        await self.websocket.send(json.dumps({
            "type": "output",
            "text": message
        }))

    async def get_user_input(self, prompt: str = "") -> str:
        """Get input from WebSocket client"""
        import json
        if prompt:
            await self.websocket.send(json.dumps({
                "type": "prompt",
                "text": prompt
            }))

        # Wait for user message from queue
        message = await self.receive_queue.get()
        return message

    async def send_log(self, message: str, level: str = "info") -> None:
        """Send log to WebSocket client"""
        import json
        import os
        if os.getenv("DEBUG", "0") == "1":
            await self.websocket.send(json.dumps({
                "type": "log",
                "text": message,
                "level": level
            }))