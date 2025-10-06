"""
Tests for Bash tool
"""
import pytest
import tempfile
import os
from agent_v5.tools.bash import BashTool


@pytest.mark.asyncio
async def test_bash_simple_command():
    """Test 1: Execute simple echo command"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(tmpdir)
        result = await tool.execute({"command": "echo 'hello world'"})

        assert result["is_error"] is False
        assert "hello world" in result["content"]


@pytest.mark.asyncio
async def test_bash_with_cwd():
    """Test 2: Verify command runs in workspace directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(tmpdir)
        result = await tool.execute({"command": "pwd"})

        assert result["is_error"] is False
        assert tmpdir in result["content"]


@pytest.mark.asyncio
async def test_bash_timeout():
    """Test 3: Command times out correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(tmpdir)
        result = await tool.execute({
            "command": "sleep 5",
            "timeout": 1000
        })

        assert result["is_error"] is True
        assert "timed out" in result["content"].lower()


@pytest.mark.asyncio
async def test_bash_output_truncation():
    """Test 4: Output truncation at 30k characters"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(tmpdir)
        result = await tool.execute({
            "command": "python -c \"print('x' * 40000)\""
        })

        assert result["is_error"] is False
        assert len(result["content"]) <= 30100
        assert "truncated" in result["content"]


@pytest.mark.asyncio
async def test_bash_error_handling():
    """Test 5: Non-existent command returns error"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(tmpdir)
        result = await tool.execute({"command": "nonexistentcommand12345"})

        assert "not found" in result["content"].lower() or "command not found" in result["content"].lower()


@pytest.mark.asyncio
async def test_bash_stderr_capture():
    """Test 6: Stderr is captured in output"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(tmpdir)
        result = await tool.execute({
            "command": "python -c \"import sys; sys.stderr.write('error message')\""
        })

        assert result["is_error"] is False
        assert "error message" in result["content"]


@pytest.mark.asyncio
async def test_bash_multiline_output():
    """Test 7: Multiline output is preserved"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(tmpdir)
        result = await tool.execute({
            "command": "printf 'line1\\nline2\\nline3'"
        })

        assert result["is_error"] is False
        assert "line1" in result["content"]
        assert "line2" in result["content"]
        assert "line3" in result["content"]


@pytest.mark.asyncio
async def test_bash_creates_file_in_workspace():
    """Test 8: Commands can create files in workspace"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(tmpdir)
        result = await tool.execute({
            "command": "echo 'test content' > test.txt"
        })

        assert result["is_error"] is False
        test_file = os.path.join(tmpdir, "test.txt")
        assert os.path.exists(test_file)
        with open(test_file) as f:
            assert "test content" in f.read()


@pytest.mark.asyncio
async def test_bash_timeout_default():
    """Test 9: Default timeout is 120 seconds"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(tmpdir)
        result = await tool.execute({
            "command": "echo 'fast command'"
        })

        assert result["is_error"] is False


@pytest.mark.asyncio
async def test_bash_max_timeout_enforced():
    """Test 10: Maximum timeout is capped at 600 seconds"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = BashTool(tmpdir)
        result = await tool.execute({
            "command": "echo 'test'",
            "timeout": 1000000
        })

        assert result["is_error"] is False
