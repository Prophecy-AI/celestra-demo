"""Tests for EvalRunner"""
import pytest
import tempfile
import os
from pathlib import Path
from evals_v5.runner import EvalRunner


def test_runner_disabled_by_default():
    """Test 1: Runner disabled when EVALS_ENABLED not set"""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = EvalRunner("test-session", tmpdir)

        assert runner.enabled is False
        assert runner.client is None


def test_runner_enabled_with_env(monkeypatch):
    """Test 2: Runner enabled when EVALS_ENABLED=1"""
    monkeypatch.setenv("EVALS_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

    with tempfile.TemporaryDirectory() as tmpdir:
        runner = EvalRunner("test-session", tmpdir)

        assert runner.enabled is True
        assert runner.client is not None


def test_runner_creates_evals_dir(monkeypatch):
    """Test 3: Runner creates .evals directory in workspace"""
    monkeypatch.setenv("EVALS_ENABLED", "1")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test-123")

    with tempfile.TemporaryDirectory() as tmpdir:
        runner = EvalRunner("test-session", tmpdir)

        evals_dir = Path(tmpdir) / ".evals"
        assert evals_dir.exists()
        assert evals_dir.is_dir()


def test_submit_does_nothing_when_disabled():
    """Test 4: submit() is no-op when disabled"""
    with tempfile.TemporaryDirectory() as tmpdir:
        runner = EvalRunner("test-session", tmpdir)

        # Should not raise, just return
        runner.submit("sql", {"sql": "SELECT 1", "context": "test"})

        # No .evals dir should be created
        evals_dir = Path(tmpdir) / ".evals"
        assert not evals_dir.exists()
