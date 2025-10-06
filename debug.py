"""Ultra-minimal debug logging - DEBUG=1 to enable"""
import os, time, functools

_D = os.getenv("DEBUG") == "1"
_C = "\033[2m", "\033[2;32m", "\033[2;31m", "\033[0m"  # dim, green, red, reset

def log(m, l=0):
    """Log if DEBUG=1. l: 0=info, 1=success, 2=error"""
    _D and print(f"{_C[l]}[{time.strftime('%H:%M:%S')}] {m}{_C[3]}", flush=True)

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
