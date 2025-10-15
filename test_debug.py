"""Tests for debug utility"""
import pytest
import os
from io import StringIO
from unittest.mock import patch


def test_log_disabled_by_default(monkeypatch):
    """Test 1: No output when DEBUG not set"""
    monkeypatch.delenv("DEBUG", raising=False)

    # Reimport to pick up env change
    import importlib
    import debug as debug_module
    importlib.reload(debug_module)

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        debug_module.log("test message")
        assert mock_stdout.getvalue() == ""


def test_log_enabled_with_debug_1(monkeypatch):
    """Test 2: Output when DEBUG=1"""
    monkeypatch.setenv("DEBUG", "1")

    import importlib
    import debug as debug_module
    importlib.reload(debug_module)

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        debug_module.log("test message")
        output = mock_stdout.getvalue()
        assert "test message" in output
        assert "[" in output  # timestamp


def test_log_levels(monkeypatch):
    """Test 3: Different log levels have different colors"""
    monkeypatch.setenv("DEBUG", "1")

    import importlib
    import debug as debug_module
    importlib.reload(debug_module)

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        debug_module.log("info", 0)
        debug_module.log("success", 1)
        debug_module.log("error", 2)
        output = mock_stdout.getvalue()

        assert "info" in output
        assert "success" in output
        assert "error" in output
        assert "\033[" in output  # ANSI codes present


@pytest.mark.asyncio
async def test_trace_decorator_logs_execution(monkeypatch):
    """Test 4: @trace decorator logs function entry/exit"""
    monkeypatch.setenv("DEBUG", "1")

    import importlib
    import debug as debug_module
    importlib.reload(debug_module)

    @debug_module.trace("test_func")
    async def test_func():
        return "result"

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        result = await test_func()
        output = mock_stdout.getvalue()

        assert result == "result"
        assert "→ test_func" in output  # entry
        assert "✓ test_func" in output  # exit


@pytest.mark.asyncio
async def test_trace_decorator_logs_exceptions(monkeypatch):
    """Test 5: @trace decorator logs exceptions"""
    monkeypatch.setenv("DEBUG", "1")

    import importlib
    import debug as debug_module
    importlib.reload(debug_module)

    @debug_module.trace("failing_func")
    async def failing_func():
        raise ValueError("test error")

    with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
        with pytest.raises(ValueError):
            await failing_func()

        output = mock_stdout.getvalue()
        assert "→ failing_func" in output
        assert "✗ failing_func" in output
        assert "test error" in output
