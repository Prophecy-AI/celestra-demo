"""
Tests for Read tool
"""
import pytest
import tempfile
import os
from agent_v5.tools.read import ReadTool


@pytest.mark.asyncio
async def test_read_simple_file():
    """Test 1: Read basic text file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Hello World\n")

        tool = ReadTool(tmpdir)
        result = await tool.execute({"file_path": test_file})

        assert result["is_error"] is False
        assert "Hello World" in result["content"]


@pytest.mark.asyncio
async def test_read_with_line_numbers():
    """Test 2: Verify cat -n format with arrow"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("line1\nline2\nline3\n")

        tool = ReadTool(tmpdir)
        result = await tool.execute({"file_path": test_file})

        assert result["is_error"] is False
        assert "     1→line1" in result["content"]
        assert "     2→line2" in result["content"]
        assert "     3→line3" in result["content"]


@pytest.mark.asyncio
async def test_read_with_offset():
    """Test 3: Read from line 10"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            for i in range(20):
                f.write(f"line {i}\n")

        tool = ReadTool(tmpdir)
        result = await tool.execute({
            "file_path": test_file,
            "offset": 10
        })

        assert result["is_error"] is False
        assert "    11→line 10" in result["content"]
        assert "     1→" not in result["content"]


@pytest.mark.asyncio
async def test_read_with_limit():
    """Test 4: Read only 5 lines"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            for i in range(20):
                f.write(f"line {i}\n")

        tool = ReadTool(tmpdir)
        result = await tool.execute({
            "file_path": test_file,
            "limit": 5
        })

        assert result["is_error"] is False
        lines = result["content"].strip().split("\n")
        assert len(lines) == 5


@pytest.mark.asyncio
async def test_read_line_truncation():
    """Test 5: Line >2000 chars is truncated"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("x" * 3000 + "\n")

        tool = ReadTool(tmpdir)
        result = await tool.execute({"file_path": test_file})

        assert result["is_error"] is False
        assert "truncated" in result["content"]


@pytest.mark.asyncio
async def test_read_empty_file():
    """Test 6: Verify warning message for empty file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "empty.txt")
        with open(test_file, "w") as f:
            pass

        tool = ReadTool(tmpdir)
        result = await tool.execute({"file_path": test_file})

        assert result["is_error"] is False
        assert "empty" in result["content"].lower()


@pytest.mark.asyncio
async def test_read_file_not_found():
    """Test 7: Non-existent file returns error"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = ReadTool(tmpdir)
        result = await tool.execute({"file_path": "/nonexistent/file.txt"})

        assert result["is_error"] is True
        assert "not found" in result["content"].lower()


@pytest.mark.asyncio
async def test_read_relative_path():
    """Test 8: Relative path is resolved to workspace"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("relative path test\n")

        tool = ReadTool(tmpdir)
        result = await tool.execute({"file_path": "test.txt"})

        assert result["is_error"] is False
        assert "relative path test" in result["content"]


@pytest.mark.asyncio
async def test_read_absolute_path():
    """Test 9: Absolute path works correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("absolute path test\n")

        tool = ReadTool(tmpdir)
        result = await tool.execute({"file_path": test_file})

        assert result["is_error"] is False
        assert "absolute path test" in result["content"]
