#!/usr/bin/env python3
"""
Simple test client for WebSocket server
"""
import asyncio
import json
import websockets


async def test_client():
    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as websocket:
        print("Connected to server")

        # Wait for connection status
        response = await websocket.recv()
        data = json.loads(response)
        print(f"Server: {data}")

        # Send a test query
        query = "Find top 3 prescribers of HUMIRA in California"
        print(f"\nSending query: {query}")

        await websocket.send(json.dumps({
            "type": "message",
            "text": query
        }))

        # Receive responses
        while True:
            try:
                response = await websocket.recv()
                data = json.loads(response)

                if data.get("type") == "output":
                    print(f"\n📝 Output: {data.get('text')}")
                elif data.get("type") == "status":
                    print(f"⚡ Status: {data.get('state')}")
                    if data.get("state") == "complete":
                        print("\n✅ Query completed!")
                        break
                elif data.get("type") == "log":
                    print(f"🔍 Log: {data.get('text')}")
                elif data.get("type") == "error":
                    print(f"❌ Error: {data.get('text')}")
                    break
                elif data.get("type") == "prompt":
                    print(f"❓ Prompt: {data.get('text')}")
                    # For testing, just send END to close
                    await websocket.send(json.dumps({
                        "type": "message",
                        "text": "END"
                    }))

            except websockets.exceptions.ConnectionClosed:
                print("Connection closed")
                break
            except Exception as e:
                print(f"Error: {e}")
                break


if __name__ == "__main__":
    print("🚀 WebSocket Test Client")
    print("=" * 40)
    asyncio.run(test_client())