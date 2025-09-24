"""
WebSocket handler for async communication
"""
import asyncio
import json
import os
from typing import Any
from queue import Queue
import threading


class AsyncWebSocketHandler:
    """Async WebSocket IO handler that bridges sync and async worlds"""

    def __init__(self, websocket: Any):
        self.websocket = websocket
        self.loop = asyncio.get_event_loop()

    def send_output(self, message: str) -> None:
        """Send output to WebSocket client (sync wrapper for async)"""
        try:
            asyncio.run_coroutine_threadsafe(
                self._send_output_async(message),
                self.loop
            ).result(timeout=5.0)  # Add timeout to prevent indefinite blocking
        except Exception as e:
            print(f"Error sending output: {e}")

    async def _send_output_async(self, message: str) -> None:
        """Async send output"""
        await self.websocket.send(json.dumps({
            "type": "output",
            "text": message
        }))

    def get_user_input(self, prompt: str = "") -> str:
        """Get input from WebSocket client (sync wrapper for async)"""
        return asyncio.run_coroutine_threadsafe(
            self._get_user_input_async(prompt),
            self.loop
        ).result()

    async def _get_user_input_async(self, prompt: str = "") -> str:
        """Async get user input"""
        if prompt:
            await self.websocket.send(json.dumps({
                "type": "prompt",
                "text": prompt
            }))

        # Send status to indicate waiting for input
        await self.websocket.send(json.dumps({
            "type": "status",
            "state": "waiting"
        }))

        # Wait for next message from client
        while True:
            message = await self.websocket.recv()
            data = json.loads(message)

            if data.get("type") == "message":
                text = data.get("text", "")

                # Send processing status
                await self.websocket.send(json.dumps({
                    "type": "status",
                    "state": "processing"
                }))

                return text

    def send_log(self, message: str, level: str = "info") -> None:
        """Send log to WebSocket client (sync wrapper for async)"""
        if os.getenv("DEBUG", "0") == "1":
            asyncio.run_coroutine_threadsafe(
                self._send_log_async(message, level),
                self.loop
            ).result()

    async def _send_log_async(self, message: str, level: str = "info") -> None:
        """Async send log"""
        await self.websocket.send(json.dumps({
            "type": "log",
            "text": message,
            "level": level
        }))