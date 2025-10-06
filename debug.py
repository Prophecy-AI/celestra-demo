"""Ultra-minimal debug logging - DEBUG=1 to enable"""
import os, time, functools, contextvars

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
