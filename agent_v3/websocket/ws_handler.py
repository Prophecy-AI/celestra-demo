"""
WebSocket handler for async communication
"""
import asyncio
import json
import os
from typing import Any
from queue import Queue
import threading
import websockets.exceptions
from agent_v3.exceptions import ConnectionLostError


class AsyncWebSocketHandler:
    """Async WebSocket IO handler that bridges sync and async worlds"""

    def __init__(self, websocket: Any, state_callback=None):
        self.websocket = websocket
        self.loop = asyncio.get_event_loop()
        self.state_callback = state_callback  # Callback to update session state

    def send_output(self, message: str) -> None:
        """Send output to WebSocket client (sync wrapper for async)"""
        # Update state to streaming when sending output
        if self.state_callback:
            from agent_v3.websocket.server import SessionState
            self.state_callback(SessionState.STREAMING)

        try:
            asyncio.run_coroutine_threadsafe(
                self._send_output_async(message),
                self.loop
            ).result(timeout=5.0)  # Add timeout to prevent indefinite blocking
        except (websockets.exceptions.ConnectionClosed, 
                websockets.exceptions.ConnectionClosedOK,
                websockets.exceptions.ConnectionClosedError) as e:
            # Re-raise as ConnectionLostError to stop orchestrator execution
            raise ConnectionLostError(f"WebSocket connection closed: {e}")
        except Exception as e:
            print(f"Error sending output: {e}")

    async def _send_output_async(self, message: str) -> None:
        """Async send output"""
        await self.websocket.send(json.dumps({
            "type": "output",
            "text": message
        }))

    def send_reasoning_trace(self, trace: str) -> None:
        """Send reasoning trace to WebSocket client (sync wrapper for async)"""
        try:
            asyncio.run_coroutine_threadsafe(
                self._send_reasoning_trace_async(trace),
                self.loop
            ).result(timeout=5.0)
        except (websockets.exceptions.ConnectionClosed, 
                websockets.exceptions.ConnectionClosedOK,
                websockets.exceptions.ConnectionClosedError) as e:
            raise ConnectionLostError(f"WebSocket connection closed: {e}")
        except Exception as e:
            print(f"Error sending reasoning trace: {e}")

    async def _send_reasoning_trace_async(self, trace: str) -> None:
        """Async send reasoning trace"""
        await self.websocket.send(json.dumps({
            "type": "reasoning",
            "text": trace
        }))

    def send_data_table(self, data: list, filename: str, session_id: str) -> None:
        """Send data table to WebSocket client (sync wrapper for async)"""
        try:
            asyncio.run_coroutine_threadsafe(
                self._send_data_table_async(data, filename, session_id),
                self.loop
            ).result(timeout=5.0)
        except (websockets.exceptions.ConnectionClosed, 
                websockets.exceptions.ConnectionClosedOK,
                websockets.exceptions.ConnectionClosedError) as e:
            raise ConnectionLostError(f"WebSocket connection closed: {e}")
        except Exception as e:
            print(f"Error sending data table: {e}")

    async def _send_data_table_async(self, data: list, filename: str, session_id: str) -> None:
        """Async send data table"""
        await self.websocket.send(json.dumps({
            "type": "data_table",
            "data": data,
            "filename": filename,
            "sessionId": session_id
        }))

    def send_action_status(self, action: str, description: str) -> None:
        """Send action status to WebSocket client (sync wrapper for async)"""
        try:
            asyncio.run_coroutine_threadsafe(
                self._send_action_status_async(action, description),
                self.loop
            ).result(timeout=5.0)
        except (websockets.exceptions.ConnectionClosed, 
                websockets.exceptions.ConnectionClosedOK,
                websockets.exceptions.ConnectionClosedError) as e:
            raise ConnectionLostError(f"WebSocket connection closed: {e}")
        except Exception as e:
            print(f"Error sending action status: {e}")

    async def _send_action_status_async(self, action: str, description: str) -> None:
        """Async send action status"""
        await self.websocket.send(json.dumps({
            "type": "action_status",
            "action": action,
            "description": description
        }))

    def get_user_input(self, prompt: str = "") -> str:
        """Get input from WebSocket client (sync wrapper for async)"""
        # Update state to waiting for input
        if self.state_callback:
            from agent_v3.websocket.server import SessionState
            self.state_callback(SessionState.WAITING_INPUT)

        try:
            return asyncio.run_coroutine_threadsafe(
                self._get_user_input_async(prompt),
                self.loop
            ).result()
        except (websockets.exceptions.ConnectionClosed,
                websockets.exceptions.ConnectionClosedOK,
                websockets.exceptions.ConnectionClosedError) as e:
            # Re-raise as ConnectionLostError to stop orchestrator execution
            raise ConnectionLostError(f"WebSocket connection closed: {e}")
        except Exception as e:
            raise

    async def _get_user_input_async(self, prompt: str = "") -> str:
        """Async get user input"""
        if prompt:
            await self.websocket.send(json.dumps({
                "type": "prompt",
                "text": prompt
            }))

        # Send state update to indicate waiting for input
        await self.websocket.send(json.dumps({
            "type": "state",
            "value": "waiting_input"
        }))

        # Wait for next message from client
        while True:
            message = await self.websocket.recv()
            data = json.loads(message)

            if data.get("type") == "message":
                text = data.get("text", "")

                # Update state back to processing
                if self.state_callback:
                    from agent_v3.websocket.server import SessionState
                    self.state_callback(SessionState.PROCESSING)

                await self.websocket.send(json.dumps({
                    "type": "state",
                    "value": "processing"
                }))

                return text

    def send_log(self, message: str, level: str = "info") -> None:
        """Send log to WebSocket client (sync wrapper for async)"""
        if os.getenv("DEBUG", "0") == "1":
            try:
                asyncio.run_coroutine_threadsafe(
                    self._send_log_async(message, level),
                    self.loop
                ).result()
            except (websockets.exceptions.ConnectionClosed,
                    websockets.exceptions.ConnectionClosedOK,
                    websockets.exceptions.ConnectionClosedError):
                # Silently skip logs if connection is closed (logs are optional)
                pass
            except Exception:
                # Silently ignore other log errors - they're not critical
                pass

    async def _send_log_async(self, message: str, level: str = "info") -> None:
        """Async send log"""
        await self.websocket.send(json.dumps({
            "type": "log",
            "text": message,
            "level": level
        }))