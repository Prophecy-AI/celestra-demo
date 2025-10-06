"""Langfuse integration for LLM observability"""
import os
from langfuse import Langfuse, observe, get_client

_client = None


def setup():
    """Setup Langfuse client - enabled when LANGFUSE_ENABLED=1"""
    global _client

    if _client or os.getenv("LANGFUSE_ENABLED") != "1":
        return _client

    # Check for required credentials
    public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
    secret_key = os.getenv("LANGFUSE_SECRET_KEY")

    if not public_key or not secret_key:
        print("LANGFUSE_ENABLED=1 but missing LANGFUSE_PUBLIC_KEY or LANGFUSE_SECRET_KEY")
        return None

    _client = Langfuse(
        public_key=public_key,
        secret_key=secret_key,
        host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com")
    )

    return _client


def trace_run(session_id: str, workspace_dir: str):
    """Decorator for observing agent runs"""
    def decorator(fn):
        @observe()
        async def wrapper(*args, **kwargs):
            if os.getenv("LANGFUSE_ENABLED") == "1":
                langfuse = get_client()
                langfuse.update_current_trace(
                    session_id=session_id,
                    user_id="agent_v5",
                    metadata={"workspace": workspace_dir}
                )
            async for message in fn(*args, **kwargs):
                yield message
        return wrapper
    return decorator
