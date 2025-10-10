# Agent V4 - Local Interactive REPL (THIS IS ONLY KEPT HERE FOR DOCUMENTATION AND SHOWING THE EVOLUTION OF AGENT V5 BASED ON CLAUDE CODE SDK)

Interactive research assistant with Claude Code SDK, sandboxed code execution, and direct BigQuery access.

## Architecture

```
Local Terminal:
  - chat.py REPL
  - Credentials in .env (NEVER leave your machine)
  - Session ID generated once per conversation

  Each message:
    ↓ (encrypted Modal RPC)

Modal Sandbox (fresh container per message):
  - Receives: session_id + message + credentials (as parameters)
  - Mounts: Shared volume at /workspace
  - Uses: /workspace/{session_id}/ (isolated per session)
  - Credentials loaded in memory only (NEVER written to disk)
  - Claude SDK + BigQuery tools
  - Code execution in isolation
  - Commits changes to volume
  - Returns response
  - Container destroyed (credentials gone)

Modal Volume (persistent):
  - Shared volume: agent-workspaces
  - /workspace/abc-123/ (session 1 files persist)
  - /workspace/xyz-456/ (session 2 files persist)
  - Complete isolation between sessions via directories
```

## Features

✨ **Interactive REPL** - Natural conversation in your terminal
✨ **Sandboxed** - Code runs in isolated Modal container per message
✨ **Persistent workspace** - Files survive across conversation in session directory
✨ **Secure** - Credentials stay local, passed as encrypted parameters
✨ **Direct BigQuery** - Agent queries BQ from sandbox (credentials in memory only)
✨ **Optimized** - 5 warm containers (sub-second latency after warmup)
✨ **Session isolation** - Each session has completely isolated workspace

## Setup

```bash
# Ensure .env has:
# ANTHROPIC_API_KEY=sk-ant-...
# GCP_PROJECT=your-project
# GCP_SERVICE_ACCOUNT_JSON={"type":"service_account",...}
```

## Usage

```bash
modal run agent_v4/main.py
```

That's it! Modal will automatically hydrate the app and start the interactive REPL.

**Example session:**

```
================================================================================
🤖 Agent V4 - Interactive Research Assistant
================================================================================
Session: abc-123
Workspace: /workspace/abc-123/ (persists across messages)
Type 'exit' to quit
================================================================================

You: Find top 10 HUMIRA prescribers in California

⏳ Processing...

Agent:
--------------------------------------------------------------------------------
I'll query BigQuery for the top HUMIRA prescribers in California.

[Executes SQL query]
Saved 10 rows to humira_ca.csv

Here are the top 10 HUMIRA prescribers in California:

1. NPI 1234567890 - 5,420 prescriptions
2. NPI 0987654321 - 4,890 prescriptions
...
--------------------------------------------------------------------------------

You: Create a bar chart from that data

⏳ Processing...

Agent:
--------------------------------------------------------------------------------
I'll create a bar chart from the humira_ca.csv file.

[Reads humira_ca.csv from /workspace/abc-123/]
[Writes Python script]
[Executes: python create_chart.py]

Chart saved to chart.png
--------------------------------------------------------------------------------

You: exit

👋 Goodbye!
```

## How It Works

1. **You type a message** in the REPL
2. **chat.py calls agent_turn.remote()** with:
   - session_id (same for entire conversation)
   - your message
   - GCP credentials from .env (encrypted in transit via Modal RPC)
3. **Modal spins up container** (or uses warm one from pool)
4. **Volume mounted** at `/workspace` (shared volume)
5. **Session directory** created/accessed: `/workspace/{session_id}/`
6. **Credentials loaded** into memory via `service_account.Credentials.from_service_account_info()` (NEVER written to disk)
7. **Claude SDK processes** with BigQuery access
   - Can query BQ using in-memory credentials
   - Can read/write files in `/workspace/{session_id}/`
   - Can execute Python/Bash in sandbox
8. **Changes committed** to volume via `workspace_volume.commit()`
9. **Returns response**
10. **Container destroyed** (credentials gone from memory)
11. **Volume persists** with session files
12. **REPL prints response**, ready for next message

## Security

✅ **NO public API** - Only callable from your machine via Modal RPC
✅ **Credentials never stored** - Passed as encrypted parameters, loaded in memory only
✅ **No credential files** - Uses `service_account.Credentials.from_service_account_info(dict)`
✅ **Encrypted in transit** - Modal's secure RPC protocol
✅ **Isolated execution** - Fresh container per message
✅ **Session isolation** - Each session has completely separate workspace directory

## Workspace Persistence

Same session_id = same workspace throughout conversation:

```
Session: abc-123

Message 1: Query BQ → saves results.csv to /workspace/abc-123/results.csv
Message 2: Read results.csv (still there!) → create chart.png
Message 3: Read chart.png (still there!) → analyze and respond

All files in /workspace/abc-123/ persist across messages in this session.
```

Different sessions = completely isolated:
```
Session: abc-123 → /workspace/abc-123/ (isolated)
Session: xyz-456 → /workspace/xyz-456/ (isolated)
```

## Configuration

**Modal function:**
- `keep_warm=5` - 5 warm containers (adjust as needed)
- `timeout=600` - 10 min per message
- Volume: `agent-workspaces` - Shared volume, auto-created
- Volume mount: `/workspace` - Each session uses `/workspace/{session_id}/`

**Local .env:**
- `ANTHROPIC_API_KEY` - Your Anthropic API key
- `GCP_PROJECT` - Your GCP project ID
- `GCP_SERVICE_ACCOUNT_JSON` - Full service account JSON (as string)

## Files

- `main.py` (133 lines) - Modal function
- `chat.py` (62 lines) - Local REPL
- `README.md` - This file

## Performance

**Cold start:** ~5-10s (first message or no warm containers)
**Warm start:** <1s (when warm pool available)

Adjust `keep_warm` in main.py based on usage:
- Development: `keep_warm=1`
- Production: `keep_warm=5-10`

## Why Shared Volume with Session Directories?

Modal does NOT support passing volumes as parameters to `.remote()` calls. Volumes must be mounted at function definition time in the `@app.function()` decorator.

Therefore, we use:
- **One shared volume** mounted at `/workspace`
- **Session-specific directories** within that volume (`/workspace/{session_id}/`)
- **Complete isolation** between sessions (different directories)
- **Persistence** across messages within same session

This is the standard Modal pattern for multi-session isolation.
