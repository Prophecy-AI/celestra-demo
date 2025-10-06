"""Tests for OpenTelemetry"""
import pytest
import os


def test_otel_disabled_by_default(monkeypatch):
    """Test 1: OTEL disabled when env not set"""
    monkeypatch.delenv("OTEL_ENABLED", raising=False)

    import importlib
    from observability import otel
    importlib.reload(otel)

    # Should not raise
    otel.setup()


def test_otel_setup_called_multiple_times(monkeypatch):
    """Test 2: setup() can be called multiple times safely"""
    monkeypatch.setenv("OTEL_ENABLED", "1")

    import importlib
    from observability import otel
    importlib.reload(otel)

    # Should not raise on multiple calls
    otel.setup()
    otel.setup()
