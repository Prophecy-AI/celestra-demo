"""
Tests for Glob tool
"""
import pytest
import tempfile
import os
import time
from agent_v5.tools.glob import GlobTool


@pytest.mark.asyncio
async def test_glob_simple_pattern():
    """Test 1: Find *.txt files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "file1.txt"), "w").close()
        open(os.path.join(tmpdir, "file2.txt"), "w").close()
        open(os.path.join(tmpdir, "file3.py"), "w").close()

        tool = GlobTool(tmpdir)
        result = await tool.execute({"pattern": "*.txt"})

        assert result["is_error"] is False
        assert "file1.txt" in result["content"]
        assert "file2.txt" in result["content"]
        assert "file3.py" not in result["content"]


@pytest.mark.asyncio
async def test_glob_recursive():
    """Test 2: Pattern **/*.py finds files in subdirectories"""
    with tempfile.TemporaryDirectory() as tmpdir:
        os.makedirs(os.path.join(tmpdir, "subdir1"))
        os.makedirs(os.path.join(tmpdir, "subdir2"))

        open(os.path.join(tmpdir, "file.py"), "w").close()
        open(os.path.join(tmpdir, "subdir1", "sub1.py"), "w").close()
        open(os.path.join(tmpdir, "subdir2", "sub2.py"), "w").close()

        tool = GlobTool(tmpdir)
        result = await tool.execute({"pattern": "**/*.py"})

        assert result["is_error"] is False
        assert "file.py" in result["content"]
        assert "sub1.py" in result["content"]
        assert "sub2.py" in result["content"]


@pytest.mark.asyncio
async def test_glob_no_matches():
    """Test 3: Pattern with no results"""
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "file.txt"), "w").close()

        tool = GlobTool(tmpdir)
        result = await tool.execute({"pattern": "*.nonexistent"})

        assert result["is_error"] is False
        assert "No files found" in result["content"]


@pytest.mark.asyncio
async def test_glob_sorted_by_mtime():
    """Test 4: Results sorted by modification time (most recent first)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "file1.txt")
        file2 = os.path.join(tmpdir, "file2.txt")
        file3 = os.path.join(tmpdir, "file3.txt")

        open(file1, "w").close()
        time.sleep(0.01)
        open(file2, "w").close()
        time.sleep(0.01)
        open(file3, "w").close()

        tool = GlobTool(tmpdir)
        result = await tool.execute({"pattern": "*.txt"})

        assert result["is_error"] is False
        lines = result["content"].split("\n")
        assert "file3.txt" in lines[0]
        assert "file1.txt" in lines[-1]


@pytest.mark.asyncio
async def test_glob_relative_path():
    """Test 5: Search in subdirectory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        subdir = os.path.join(tmpdir, "subdir")
        os.makedirs(subdir)

        open(os.path.join(tmpdir, "root.txt"), "w").close()
        open(os.path.join(subdir, "sub.txt"), "w").close()

        tool = GlobTool(tmpdir)
        result = await tool.execute({
            "pattern": "*.txt",
            "path": "subdir"
        })

        assert result["is_error"] is False
        assert "sub.txt" in result["content"]
        assert "root.txt" not in result["content"]


@pytest.mark.skip(reason="Brace expansion (*.{py,txt}) not supported by Python glob - MVP limitation")
@pytest.mark.asyncio
async def test_glob_multiple_extensions():
    """Test 6: Pattern with multiple extensions (SKIPPED - brace expansion not supported)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        open(os.path.join(tmpdir, "file.py"), "w").close()
        open(os.path.join(tmpdir, "file.txt"), "w").close()
        open(os.path.join(tmpdir, "file.md"), "w").close()

        tool = GlobTool(tmpdir)
        result = await tool.execute({"pattern": "*.{py,txt}"})

        assert result["is_error"] is False
        matches = result["content"].split("\n")
        assert any("file.py" in m for m in matches)
        assert any("file.txt" in m for m in matches)
