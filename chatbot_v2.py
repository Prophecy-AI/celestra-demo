#!/usr/bin/env python3
"""
Minimal WebSocket chatbot with proper state management
"""
import asyncio
import json
import websockets
import sys
from enum import Enum


class ServerState(Enum):
    IDLE = "idle"
    PROCESSING = "processing"
    STREAMING = "streaming"
    WAITING_INPUT = "waiting_input"


class Chatbot:
    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.ws = None
        self.state = ServerState.IDLE
        self.running = True

    async def connect(self):
        """Establish WebSocket connection"""
        self.ws = await websockets.connect(self.uri)

        # Get initial connection message
        msg = await self.ws.recv()
        data = json.loads(msg)
        if data.get("type") == "status" and data.get("state") == "connected":
            print(f"✅ Connected to session {data.get('session_id')}\n")

    async def send(self, text: str):
        """Send message to server (only when allowed)"""
        if self.state not in [ServerState.IDLE, ServerState.WAITING_INPUT]:
            print(f"⚠️  Cannot send - server is {self.state.value}")
            return False

        await self.ws.send(json.dumps({
            "type": "message",
            "text": text
        }))
        return True

    async def handle_message(self, data: dict):
        """Process incoming message based on type"""
        msg_type = data.get("type")

        if msg_type == "state":
            # Update our state to match server
            new_state = data.get("value")
            self.state = ServerState(new_state)

            # Visual feedback for state changes
            if self.state == ServerState.PROCESSING:
                print("⚡ Processing...", flush=True)
            elif self.state == ServerState.WAITING_INPUT:
                print("❓ ", end="", flush=True)
            elif self.state == ServerState.IDLE:
                print("✅ Ready\n", flush=True)
            # STREAMING state doesn't print anything

        elif msg_type == "output":
            # Direct output from agent
            print(data.get("text", ""))

        elif msg_type == "prompt":
            # Server is asking for input
            print(data.get("text", ""), end="", flush=True)

        elif msg_type == "status":
            # Status updates
            if data.get("state") == "complete":
                print("\n✅ Complete!\n")

        elif msg_type == "error":
            print(f"❌ Error: {data.get('text')}")

        elif msg_type == "log" and "--debug" in sys.argv:
            print(f"[DEBUG] {data.get('text')}")

    async def receive_loop(self):
        """Continuously receive and handle messages"""
        try:
            while self.running:
                msg = await self.ws.recv()
                data = json.loads(msg)
                await self.handle_message(data)
        except websockets.ConnectionClosed:
            print("\n🔌 Connection lost")
            self.running = False

    async def input_loop(self):
        """Handle user input (respects state)"""
        loop = asyncio.get_event_loop()

        print("💬 Healthcare Data Chatbot")
        print("Commands: quit, exit, bye to end\n")

        while self.running:
            try:
                # Get input asynchronously to not block receive loop
                user_input = await loop.run_in_executor(
                    None,
                    lambda: input("👤 You: ")
                )

                # Handle exit commands
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("👋 Goodbye!")
                    self.running = False
                    break

                # Send if we have input and state allows
                if user_input.strip():
                    sent = await self.send(user_input)
                    if not sent:
                        # Message was blocked, input will be discarded
                        print("   (Message blocked - try again when ready)")

            except EOFError:
                # Ctrl+D pressed
                self.running = False
                break
            except KeyboardInterrupt:
                # Ctrl+C pressed
                print("\n\n🛑 Interrupted")
                self.running = False
                break

    async def run(self):
        """Main entry point"""
        try:
            await self.connect()

            # Start both loops concurrently
            receive_task = asyncio.create_task(self.receive_loop())
            input_task = asyncio.create_task(self.input_loop())

            # Wait for either to complete
            done, pending = await asyncio.wait(
                [receive_task, input_task],
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel the other task
            for task in pending:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        except websockets.WebSocketException as e:
            print(f"❌ Connection error: {e}")
        except KeyboardInterrupt:
            print("\n🛑 Shutting down...")
        finally:
            if self.ws:
                await self.ws.close()


async def main():
    """Main function"""
    # Parse command line
    uri = "ws://localhost:8765"

    for i, arg in enumerate(sys.argv[1:]):
        if arg.startswith("ws://") or arg.startswith("wss://"):
            uri = arg
        elif arg == "--help":
            print("Usage: python chatbot_v2.py [ws://host:port] [--debug]")
            print("Default: ws://localhost:8765")
            sys.exit(0)

    print(f"🔗 Connecting to {uri}...")

    # Run chatbot
    bot = Chatbot(uri)
    await bot.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bye!")