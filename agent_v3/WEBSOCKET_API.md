# WebSocket API Documentation

## Overview
Agent v3 supports WebSocket connections for remote interaction while maintaining full CLI compatibility.

## Starting the Server
```bash
# Default (localhost:8765)
python -m agent_v3.websocket.server

# Custom host/port
python -m agent_v3.websocket.server --host 0.0.0.0 --port 8080 --debug
```

## Protocol

### Client → Server Messages

```json
{"type": "message", "text": "Find prescribers of HUMIRA"}
{"type": "ping"}
```

### Server → Client Messages

```json
{"type": "output", "text": "Assistant message"}
{"type": "log", "text": "Debug log", "level": "info"}
{"type": "status", "state": "connected|processing|waiting|complete"}
{"type": "error", "text": "Error message"}
{"type": "prompt", "text": "Waiting for user input"}
```

## Example Client Usage

```python
import asyncio
import json
import websockets

async def chat():
    async with websockets.connect("ws://localhost:8765") as ws:
        # Send query
        await ws.send(json.dumps({
            "type": "message",
            "text": "Find top prescribers of HUMIRA"
        }))

        # Receive responses
        async for message in ws:
            data = json.loads(message)
            if data["type"] == "output":
                print(data["text"])
            elif data["type"] == "status" and data["state"] == "complete":
                break

asyncio.run(chat())
```

## Security Notes
- Input sanitization enforced
- Max message size: 10KB
- Connection timeout: 30 minutes idle
- Rate limiting ready (10 req/min per connection)

## Testing
```bash
# Run test client
python test_websocket_client.py
```