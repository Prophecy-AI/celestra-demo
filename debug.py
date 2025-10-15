"""Ultra-minimal debug logging - DEBUG=1 to enable"""
import os, time, functools, contextvars, json

_D = os.getenv("DEBUG") == "1"
_C = "\033[2m", "\033[2;32m", "\033[2;31m", "\033[0m"  # dim, green, red, reset
_S = contextvars.ContextVar('session', default="")

def with_session(s):
    def d(f):
        @functools.wraps(f)
        async def w(*a, **k):
            t = _S.set(s);
            try:
                async for x in f(*a, **k): yield x
            finally: _S.reset(t)
        return w
    return d

def log(m, l=0):
    """Log if DEBUG=1. l: 0=info, 1=success, 2=error"""
    s = _S.get()
    _D and print(f"{_C[l]}[{time.strftime('%H:%M:%S')}]{s and f' {s}'} {m}{_C[3]}", flush=True)

def trace(n):
    """Trace async function. @trace('name')"""
    def d(f):
        @functools.wraps(f)
        async def w(*a, **k):
            _D and log(f"→ {n}")
            try:
                r = await f(*a, **k)
                _D and log(f"✓ {n}", 1)
                return r
            except Exception as e:
                _D and log(f"✗ {n}: {e}", 2)
                raise
        return w
    return d

def log_tool_call(message):
    """Log tool call with input/output - shows exactly what LLM sees"""
    print(f"\n\n{'='*80}", flush=True)
    print(f"🔧 TOOL CALL: {message['tool_name']}", flush=True)
    print(f"{'='*80}", flush=True)
    print(f"📥 INPUT (what LLM sent):", flush=True)
    print(json.dumps(message['tool_input'], indent=2), flush=True)
    print(f"\n📤 OUTPUT (what LLM received):", flush=True)
    print(message['tool_output'], flush=True)
    print(f"{'='*80}\n", flush=True)
