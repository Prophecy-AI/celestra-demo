"""
WebSocket server with FastAPI for agent_v3
"""
import asyncio
import json
import os
import sys
import time
from datetime import datetime
from typing import Dict, Any
from enum import Enum
from pathlib import Path
import websockets
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Add parent directories to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from agent_v3.orchestrator import RecursiveOrchestrator
from agent_v3.websocket.ws_handler import AsyncWebSocketHandler


class SessionState(Enum):
    """Session states for proper flow control"""
    IDLE = "idle"
    PROCESSING = "processing"
    STREAMING = "streaming"
    WAITING_INPUT = "waiting_input"


# Create FastAPI app
app = FastAPI(title="Healthcare Data Agent API")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/download/{session_id}/{filename}")
async def download_csv(session_id: str, filename: str):
    """Download CSV file from a session"""
    # Sanitize inputs to prevent path traversal
    safe_session = os.path.basename(session_id)
    safe_filename = os.path.basename(filename)

    # Ensure it's a CSV file
    if not safe_filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="Only CSV files can be downloaded")

    # Build file path
    file_path = Path("output") / f"session_{safe_session}" / safe_filename

    # Check if file exists
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")

    # Return file
    return FileResponse(
        path=file_path,
        media_type="text/csv",
        filename=safe_filename,
        headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": "agent_v3"}


class WebSocketServer:
    """WebSocket server for agent communication"""

    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.active_sessions: Dict[str, Any] = {}
        self.session_states: Dict[str, SessionState] = {}
        self.debug = os.getenv("DEBUG", "0") == "1"

    def log(self, message: str):
        """Server logging"""
        if self.debug:
            timestamp = time.strftime('%H:%M:%S')
            print(f"[{timestamp}] [WS-SERVER] {message}")

    def _update_state(self, session_id: str, state: SessionState) -> None:
        """Update session state and notify client"""
        self.session_states[session_id] = state
        self.log(f"Session {session_id} state: {state.value}")

    async def _send_state(self, websocket, state: SessionState) -> None:
        """Send state update to client"""
        await websocket.send(json.dumps({
            "type": "state",
            "value": state.value
        }))

    async def handle_client(self, websocket):
        """Handle individual WebSocket client connection"""
        session_id = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log(f"New connection: {session_id}")

        # Initialize session state
        self.session_states[session_id] = SessionState.IDLE

        # Send welcome message
        await websocket.send(json.dumps({
            "type": "status",
            "state": "connected",
            "session_id": session_id
        }))

        # Create async IO handler for this session with state tracking
        io_handler = AsyncWebSocketHandler(websocket, lambda s: self._update_state(session_id, s))

        try:
            async for message in websocket:
                try:
                    data = json.loads(message)

                    if data.get("type") == "message":
                        # Check if we can accept messages
                        current_state = self.session_states.get(session_id, SessionState.IDLE)
                        if current_state not in [SessionState.IDLE, SessionState.WAITING_INPUT]:
                            await websocket.send(json.dumps({
                                "type": "error",
                                "text": f"Cannot accept messages while {current_state.value}"
                            }))
                            continue

                        text = data.get("text", "").strip()
                        if not text:
                            continue

                        # Update state to processing
                        self._update_state(session_id, SessionState.PROCESSING)
                        await self._send_state(websocket, SessionState.PROCESSING)

                        # Run orchestrator
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
            if session_id in self.session_states:
                del self.session_states[session_id]

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

            # Return to idle state
            self._update_state(session_id, SessionState.IDLE)
            await self._send_state(websocket, SessionState.IDLE)

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


async def run_servers():
    """Run both FastAPI and WebSocket servers concurrently"""
    import argparse

    parser = argparse.ArgumentParser(description="WebSocket + HTTP server for agent_v3")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--ws-port", type=int, default=8765, help="WebSocket port")
    parser.add_argument("--http-port", type=int, default=8766, help="HTTP API port")
    parser.add_argument("--debug", action="store_true", help="Enable debug logging")

    args = parser.parse_args()

    if args.debug:
        os.environ["DEBUG"] = "1"

    # Create WebSocket server
    ws_server = WebSocketServer(args.host, args.ws_port)

    print(f"🚀 Starting servers:")
    print(f"   WebSocket: ws://{args.host}:{args.ws_port}")
    print(f"   HTTP API:  http://{args.host}:{args.http_port}")
    print(f"📝 Debug mode: {'ON' if args.debug else 'OFF'}")
    print("Press Ctrl+C to stop\n")

    # Create tasks for both servers
    tasks = []

    # WebSocket server task
    async def run_websocket():
        async with websockets.serve(ws_server.handle_client, args.host, args.ws_port):
            await asyncio.Future()  # Run forever

    # FastAPI server task
    async def run_fastapi():
        config = uvicorn.Config(
            app=app,
            host=args.host,
            port=args.http_port,
            log_level="info" if args.debug else "error",
            access_log=args.debug
        )
        server = uvicorn.Server(config)
        await server.serve()

    # Run both servers concurrently
    tasks = [
        asyncio.create_task(run_websocket()),
        asyncio.create_task(run_fastapi())
    ]

    try:
        await asyncio.gather(*tasks)
    except KeyboardInterrupt:
        print("\n👋 Servers stopped")
        for task in tasks:
            task.cancel()


def main():
    """Main entry point"""
    try:
        asyncio.run(run_servers())
    except KeyboardInterrupt:
        print("\n👋 Shutdown complete")


if __name__ == "__main__":
    main()