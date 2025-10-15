"""Tests for Langfuse"""
import pytest
import os


def test_langfuse_disabled_by_default(monkeypatch):
    """Test 1: Langfuse disabled when env not set"""
    monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)

    import importlib
    from observability import langfuse_client
    importlib.reload(langfuse_client)

    client = langfuse_client.setup()
    assert client is None


def test_langfuse_setup_called_multiple_times(monkeypatch):
    """Test 2: setup() can be called multiple times safely"""
    monkeypatch.delenv("LANGFUSE_ENABLED", raising=False)

    import importlib
    from observability import langfuse_client
    importlib.reload(langfuse_client)

    # Should not raise on multiple calls
    langfuse_client.setup()
    langfuse_client.setup()
