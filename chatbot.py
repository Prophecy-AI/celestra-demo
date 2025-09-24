#!/usr/bin/env python3
"""
WebSocket chatbot CLI for agent_v3
"""
import asyncio
import json
import websockets
import sys
import signal
from typing import Optional

class ChatbotCLI:
    def __init__(self, uri: str = "ws://localhost:8765"):
        self.uri = uri
        self.websocket: Optional[websockets.WebSocketClientProtocol] = None
        self.running = True

    async def connect(self):
        """Connect to WebSocket server"""
        print(f"📡 Connecting to {self.uri}...")
        self.websocket = await websockets.connect(self.uri)

        # Get initial connection message
        init_msg = await self.websocket.recv()
        data = json.loads(init_msg)
        if data.get("type") == "status" and data.get("state") == "connected":
            print(f"✅ Connected! Session: {data.get('session_id')}")
        print("-" * 60)

    async def send_message(self, text: str):
        """Send message to server"""
        await self.websocket.send(json.dumps({
            "type": "message",
            "text": text
        }))

    async def receive_messages(self):
        """Receive and display messages from server"""
        while self.running:
            try:
                message = await asyncio.wait_for(self.websocket.recv(), timeout=0.5)
                data = json.loads(message)

                if data.get("type") == "output":
                    print(data.get("text", ""))
                elif data.get("type") == "status":
                    state = data.get("state")
                    if state == "processing":
                        print("\n⚡ Processing...", end="", flush=True)
                    elif state == "waiting":
                        print("\n⏳ Waiting for input...", end="", flush=True)
                    elif state == "complete":
                        print("\n✅ Complete!")
                elif data.get("type") == "prompt":
                    # Server is waiting for input
                    return "prompt"
                elif data.get("type") == "error":
                    print(f"\n❌ Error: {data.get('text')}")
                elif data.get("type") == "log" and "--debug" in sys.argv:
                    print(f"🔍 {data.get('text')}")

            except asyncio.TimeoutError:
                continue
            except websockets.exceptions.ConnectionClosed:
                print("\n🔌 Connection closed")
                self.running = False
                break
            except Exception as e:
                print(f"\n⚠️ Error: {e}")
                break

    async def user_input_handler(self):
        """Handle user input in async way"""
        loop = asyncio.get_event_loop()

        while self.running:
            try:
                # Get user input asynchronously
                user_input = await loop.run_in_executor(None, lambda: input("\n👤 You: "))

                if user_input.lower() in ['quit', 'exit', 'bye']:
                    print("\n👋 Goodbye!")
                    self.running = False
                    break

                if user_input.strip():
                    await self.send_message(user_input)

            except EOFError:
                self.running = False
                break
            except Exception as e:
                print(f"Input error: {e}")

    async def run(self):
        """Main chat loop"""
        try:
            await self.connect()

            print("\n💬 Healthcare Data Analysis Chatbot")
            print("Type 'quit' or 'exit' to end session")
            print("-" * 60)

            # Start receiving messages
            receive_task = asyncio.create_task(self.receive_messages())

            # Handle user input
            await self.user_input_handler()

            # Clean up
            receive_task.cancel()
            await self.websocket.close()

        except websockets.exceptions.WebSocketException as e:
            print(f"❌ WebSocket error: {e}")
        except KeyboardInterrupt:
            print("\n\n🛑 Interrupted")
        except Exception as e:
            print(f"❌ Error: {e}")
        finally:
            if self.websocket:
                await self.websocket.close()

def signal_handler(signum, frame):
    """Handle Ctrl+C gracefully"""
    print("\n\n🛑 Shutting down...")
    sys.exit(0)

def main():
    """Main entry point"""
    signal.signal(signal.SIGINT, signal_handler)

    # Parse arguments
    uri = "ws://localhost:8765"
    if len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        uri = sys.argv[1]

    print("🤖 Healthcare Data Analysis Chatbot")
    print("=" * 60)

    # Check if server is specified
    if "--help" in sys.argv or "-h" in sys.argv:
        print("Usage: python chatbot.py [ws://host:port] [--debug]")
        print("Default: ws://localhost:8765")
        sys.exit(0)

    # Run the chatbot
    chatbot = ChatbotCLI(uri)
    asyncio.run(chatbot.run())

if __name__ == "__main__":
    main()