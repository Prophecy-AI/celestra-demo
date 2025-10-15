"""
Tests for Write tool
"""
import pytest
import tempfile
import os
from agent_v5.tools.write import WriteTool


@pytest.mark.asyncio
async def test_write_new_file():
    """Test 1: Create new file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = WriteTool(tmpdir)
        test_file = os.path.join(tmpdir, "new_file.txt")

        result = await tool.execute({
            "file_path": test_file,
            "content": "Hello World"
        })

        assert result["is_error"] is False
        assert "created" in result["content"].lower()
        assert os.path.exists(test_file)
        with open(test_file) as f:
            assert f.read() == "Hello World"


@pytest.mark.asyncio
async def test_write_overwrite_file():
    """Test 2: Overwrite existing file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "existing.txt")
        with open(test_file, "w") as f:
            f.write("old content")

        tool = WriteTool(tmpdir)
        result = await tool.execute({
            "file_path": test_file,
            "content": "new content"
        })

        assert result["is_error"] is False
        assert "updated" in result["content"].lower()
        with open(test_file) as f:
            assert f.read() == "new content"


@pytest.mark.asyncio
async def test_write_creates_directories():
    """Test 3: Parent directories are created automatically"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = WriteTool(tmpdir)
        nested_file = os.path.join(tmpdir, "a", "b", "c", "file.txt")

        result = await tool.execute({
            "file_path": nested_file,
            "content": "nested content"
        })

        assert result["is_error"] is False
        assert os.path.exists(nested_file)
        with open(nested_file) as f:
            assert f.read() == "nested content"


@pytest.mark.asyncio
async def test_write_relative_path():
    """Test 4: Relative path is resolved to workspace"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = WriteTool(tmpdir)

        result = await tool.execute({
            "file_path": "relative.txt",
            "content": "relative content"
        })

        assert result["is_error"] is False
        test_file = os.path.join(tmpdir, "relative.txt")
        assert os.path.exists(test_file)
        with open(test_file) as f:
            assert f.read() == "relative content"


@pytest.mark.asyncio
async def test_write_absolute_path():
    """Test 5: Absolute path works correctly"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = WriteTool(tmpdir)
        abs_file = os.path.join(tmpdir, "absolute.txt")

        result = await tool.execute({
            "file_path": abs_file,
            "content": "absolute content"
        })

        assert result["is_error"] is False
        assert os.path.exists(abs_file)
        with open(abs_file) as f:
            assert f.read() == "absolute content"


@pytest.mark.asyncio
async def test_write_empty_content():
    """Test 6: Write empty string creates empty file"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = WriteTool(tmpdir)
        test_file = os.path.join(tmpdir, "empty.txt")

        result = await tool.execute({
            "file_path": test_file,
            "content": ""
        })

        assert result["is_error"] is False
        assert os.path.exists(test_file)
        with open(test_file) as f:
            assert f.read() == ""


@pytest.mark.asyncio
async def test_write_large_content():
    """Test 7: Write large content (>100kb)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = WriteTool(tmpdir)
        test_file = os.path.join(tmpdir, "large.txt")
        large_content = "x" * 150000

        result = await tool.execute({
            "file_path": test_file,
            "content": large_content
        })

        assert result["is_error"] is False
        assert os.path.exists(test_file)
        with open(test_file) as f:
            assert f.read() == large_content


@pytest.mark.asyncio
async def test_write_unicode():
    """Test 8: Write unicode characters"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = WriteTool(tmpdir)
        test_file = os.path.join(tmpdir, "unicode.txt")
        unicode_content = "Hello 世界 🌍 Привет"

        result = await tool.execute({
            "file_path": test_file,
            "content": unicode_content
        })

        assert result["is_error"] is False
        assert os.path.exists(test_file)
        with open(test_file, encoding='utf-8') as f:
            assert f.read() == unicode_content
