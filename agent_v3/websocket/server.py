"""
WebSocket server for agent_v3
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any
import websockets

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_v3.orchestrator import RecursiveOrchestrator
from agent_v3.websocket.ws_handler import AsyncWebSocketHandler


class WebSocketServer:
    """WebSocket server for agent communication"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.active_sessions: Dict[str, Any] = {}
        self.debug = os.getenv("DEBUG", "0") == "1"

    def log(self, message: str):
        """Server logging"""
        if self.debug:
            timestamp = time.strftime('%H:%M:%S')
            print(f"[{timestamp}] [WS-SERVER] {message}")

    async def handle_client(self, websocket):
        """Handle individual WebSocket client connection"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log(f"New connection: {session_id}")

        # Send welcome message
        await websocket.send(json.dumps({
            "type": "status",
            "state": "connected",
            "session_id": session_id
        }))

        # Create async IO handler for this session
        io_handler = AsyncWebSocketHandler(websocket)

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)

                    if data.get("type") == "message":
                        text = data.get("text", "").strip()

                        if not text:
                            continue

                        # Send processing status
                        await websocket.send(json.dumps({
                            "type": "status",
                            "state": "processing"
                        }))

                        # Run orchestrator in thread pool to avoid blocking
                        await self.process_message(session_id, text, io_handler, websocket)

                    elif data.get("type") == "ping":
                        # Keep-alive response
                        await websocket.send(json.dumps({"type": "pong"}))

                except json.JSONDecodeError as e:
                    await websocket.send(json.dumps({
                        "type": "error",
                        "text": f"Invalid JSON: {str(e)}"
                    }))
                except Exception as e:
                    self.log(f"Error handling message: {str(e)}")
                    await websocket.send(json.dumps({
                        "type": "error",
                        "text": f"Processing error: {str(e)}"
                    }))

        except websockets.exceptions.ConnectionClosed:
            self.log(f"Connection closed: {session_id}")
        finally:
            # Clean up session
            if session_id in self.active_sessions:
                del self.active_sessions[session_id]

    async def process_message(self, session_id: str, text: str, io_handler: Any, websocket):
        """Process incoming message through orchestrator"""
        try:
            # Create orchestrator with WebSocket IO handler
            orchestrator = RecursiveOrchestrator(
                session_id=session_id,
                debug=self.debug,
                io_handler=io_handler
            )

            # Store in active sessions
            self.active_sessions[session_id] = {
                "orchestrator": orchestrator,
                "io_handler": io_handler
            }

            # Run orchestrator in executor to not block event loop
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, orchestrator.run, text)

            # Send completion status
            await websocket.send(json.dumps({
                "type": "status",
                "state": "complete",
                "summary": result.get("summary", {})
            }))

        except Exception as e:
            self.log(f"Orchestrator error: {str(e)}")
            await websocket.send(json.dumps({
                "type": "error",
                "text": f"Agent error: {str(e)}"
            }))

    async def start(self):
        """Start the WebSocket server"""
        print(f"🚀 WebSocket server starting on ws://{self.host}:{self.port}")
        print(f"📝 Debug mode: {'ON' if self.debug else 'OFF'}")
        print("Press Ctrl+C to stop\n")

        async with websockets.serve(self.handle_client, self.host, self.port):
            await asyncio.Future()  # Run forever


def main():
    """Main entry point for WebSocket server"""
    import argparse

    parser = argparse.ArgumentParser(description="WebSocket server for agent_v3")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8765, help="Server port")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        os.environ["DEBUG"] = "1"

    server = WebSocketServer(args.host, args.port)

    try:
        asyncio.run(server.start())
    except KeyboardInterrupt:
        print("\n👋 Server stopped")


if __name__ == "__main__":
    main()