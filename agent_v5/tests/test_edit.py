"""
Tests for Edit tool
"""
import pytest
import tempfile
import os
from agent_v5.tools.edit import EditTool


@pytest.mark.asyncio
async def test_edit_single_replacement():
    """Test 1: Replace unique string"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Hello World\nGoodbye World\n")

        tool = EditTool(tmpdir)
        result = await tool.execute({
            "file_path": test_file,
            "old_string": "Hello World",
            "new_string": "Hi Universe"
        })

        assert result["is_error"] is False
        with open(test_file) as f:
            content = f.read()
            assert "Hi Universe" in content
            assert "Hello World" not in content


@pytest.mark.asyncio
async def test_edit_replace_all():
    """Test 2: Replace all occurrences"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("foo bar\nfoo baz\nfoo qux\n")

        tool = EditTool(tmpdir)
        result = await tool.execute({
            "file_path": test_file,
            "old_string": "foo",
            "new_string": "bar",
            "replace_all": True
        })

        assert result["is_error"] is False
        with open(test_file) as f:
            content = f.read()
            assert content.count("bar") == 4
            assert "foo" not in content


@pytest.mark.asyncio
async def test_edit_string_not_found():
    """Test 3: Error when string not found"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Hello World\n")

        tool = EditTool(tmpdir)
        result = await tool.execute({
            "file_path": test_file,
            "old_string": "nonexistent",
            "new_string": "replacement"
        })

        assert result["is_error"] is True
        assert "not found" in result["content"].lower()


@pytest.mark.asyncio
async def test_edit_multiple_matches_error():
    """Test 4: Error when multiple matches without replace_all"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("foo\nfoo\nfoo\n")

        tool = EditTool(tmpdir)
        result = await tool.execute({
            "file_path": test_file,
            "old_string": "foo",
            "new_string": "bar"
        })

        assert result["is_error"] is True
        assert "3 times" in result["content"]


@pytest.mark.asyncio
async def test_edit_shows_snippet():
    """Test 5: Verify output shows context snippet"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("line1\nline2\nline3\nline4\nline5\n")

        tool = EditTool(tmpdir)
        result = await tool.execute({
            "file_path": test_file,
            "old_string": "line3",
            "new_string": "MODIFIED"
        })

        assert result["is_error"] is False
        assert "MODIFIED" in result["content"]
        assert "→" in result["content"]


@pytest.mark.asyncio
async def test_edit_file_not_found():
    """Test 6: Non-existent file returns error"""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = EditTool(tmpdir)
        result = await tool.execute({
            "file_path": "/nonexistent/file.txt",
            "old_string": "old",
            "new_string": "new"
        })

        assert result["is_error"] is True
        assert "not found" in result["content"].lower()


@pytest.mark.asyncio
async def test_edit_preserve_indentation():
    """Test 7: Exact string match preserves indentation"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.py")
        with open(test_file, "w") as f:
            f.write("def foo():\n    print('hello')\n")

        tool = EditTool(tmpdir)
        result = await tool.execute({
            "file_path": test_file,
            "old_string": "    print('hello')",
            "new_string": "    print('world')"
        })

        assert result["is_error"] is False
        with open(test_file) as f:
            content = f.read()
            assert "    print('world')" in content
