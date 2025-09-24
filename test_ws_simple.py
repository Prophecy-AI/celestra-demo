#!/usr/bin/env python3
"""
Simple WebSocket test - just send a message and see what happens
"""
import asyncio
import json
import websockets
import sys


async def test():
    try:
        uri = "ws://localhost:8765"  # Different port to avoid conflicts
        print(f"Connecting to {uri}...")

        async with websockets.connect(uri) as websocket:
            print("Connected!")

            # Try to receive initial message if any
            try:
                init_msg = await asyncio.wait_for(websocket.recv(), timeout=2.0)
                print(f"Initial message: {init_msg}")
            except asyncio.TimeoutError:
                print("No initial message received")

            # Send a test query
            query = {"type": "message", "text": "Find 3 prescribers of HUMIRA"}
            print(f"Sending: {query}")
            await websocket.send(json.dumps(query))

            # Receive responses for up to 30 seconds
            end_time = asyncio.get_event_loop().time() + 30

            while asyncio.get_event_loop().time() < end_time:
                try:
                    response = await asyncio.wait_for(websocket.recv(), timeout=1.0)
                    data = json.loads(response)
                    print(f"Received: {data.get('type', 'unknown')} - {str(data)[:200]}")

                    if data.get("type") == "status" and data.get("state") == "complete":
                        print("Complete!")
                        break

                except asyncio.TimeoutError:
                    print(".", end="", flush=True)
                except Exception as e:
                    print(f"\nError: {e}")
                    break

    except Exception as e:
        print(f"Connection error: {e}")
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(test()))
