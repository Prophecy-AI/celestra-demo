"""
Tests for Grep tool
"""
import pytest
import tempfile
import os
from agent_v5.tools.grep import GrepTool


@pytest.mark.asyncio
async def test_grep_simple_pattern():
    """Test 1: Find 'test' in files"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "file1.txt")
        file2 = os.path.join(tmpdir, "file2.txt")

        with open(file1, "w") as f:
            f.write("this is a test\n")
        with open(file2, "w") as f:
            f.write("no match here\n")

        tool = GrepTool(tmpdir)
        result = await tool.execute({
            "pattern": "test",
            "output_mode": "files_with_matches"
        })

        assert result["is_error"] is False
        assert "file1.txt" in result["content"]
        assert "file2.txt" not in result["content"]


@pytest.mark.asyncio
async def test_grep_case_insensitive():
    """Test 2: Case insensitive search with -i flag"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("Hello World\n")

        tool = GrepTool(tmpdir)
        result = await tool.execute({
            "pattern": "hello",
            "-i": True,
            "output_mode": "content"
        })

        assert result["is_error"] is False
        assert "Hello World" in result["content"]


@pytest.mark.asyncio
async def test_grep_with_line_numbers():
    """Test 3: Show line numbers with -n flag"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("line 1\nline 2\nmatch here\nline 4\n")

        tool = GrepTool(tmpdir)
        result = await tool.execute({
            "pattern": "match",
            "-n": True,
            "output_mode": "content"
        })

        assert result["is_error"] is False
        assert "3:" in result["content"]
        assert "match here" in result["content"]


@pytest.mark.asyncio
async def test_grep_context_lines():
    """Test 4: Context lines with -A, -B, -C flags"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("before1\nbefore2\nMATCH\nafter1\nafter2\n")

        tool = GrepTool(tmpdir)
        result = await tool.execute({
            "pattern": "MATCH",
            "-C": 1,
            "output_mode": "content"
        })

        assert result["is_error"] is False
        assert "before2" in result["content"]
        assert "MATCH" in result["content"]
        assert "after1" in result["content"]


@pytest.mark.asyncio
async def test_grep_glob_filter():
    """Test 5: Search only *.py files with glob filter"""
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = os.path.join(tmpdir, "test.py")
        txt_file = os.path.join(tmpdir, "test.txt")

        with open(py_file, "w") as f:
            f.write("def foo(): pass\n")
        with open(txt_file, "w") as f:
            f.write("foo bar\n")

        tool = GrepTool(tmpdir)
        result = await tool.execute({
            "pattern": "foo",
            "glob": "*.py",
            "output_mode": "files_with_matches"
        })

        assert result["is_error"] is False
        assert "test.py" in result["content"]
        assert "test.txt" not in result["content"]


@pytest.mark.asyncio
async def test_grep_type_filter():
    """Test 6: Filter by file type"""
    with tempfile.TemporaryDirectory() as tmpdir:
        py_file = os.path.join(tmpdir, "script.py")
        txt_file = os.path.join(tmpdir, "doc.txt")

        with open(py_file, "w") as f:
            f.write("import sys\n")
        with open(txt_file, "w") as f:
            f.write("import data\n")

        tool = GrepTool(tmpdir)
        result = await tool.execute({
            "pattern": "import",
            "type": "py",
            "output_mode": "files_with_matches"
        })

        assert result["is_error"] is False
        assert "script.py" in result["content"]


@pytest.mark.asyncio
async def test_grep_output_modes():
    """Test 7: Test all output modes"""
    with tempfile.TemporaryDirectory() as tmpdir:
        file1 = os.path.join(tmpdir, "file1.txt")
        file2 = os.path.join(tmpdir, "file2.txt")

        with open(file1, "w") as f:
            f.write("match\nmatch\n")
        with open(file2, "w") as f:
            f.write("match\n")

        tool = GrepTool(tmpdir)

        result_files = await tool.execute({
            "pattern": "match",
            "output_mode": "files_with_matches"
        })
        assert "file1.txt" in result_files["content"]

        result_count = await tool.execute({
            "pattern": "match",
            "output_mode": "count"
        })
        assert "2" in result_count["content"]

        result_content = await tool.execute({
            "pattern": "match",
            "output_mode": "content"
        })
        assert "match" in result_content["content"]


@pytest.mark.asyncio
async def test_grep_no_matches():
    """Test 8: Pattern not found returns graceful message"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("nothing here\n")

        tool = GrepTool(tmpdir)
        result = await tool.execute({
            "pattern": "nonexistent"
        })

        assert result["is_error"] is False
        assert "No matches found" in result["content"]


@pytest.mark.asyncio
async def test_grep_multiline():
    """Test 9: Multiline pattern matching"""
    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("start\nmiddle\nend\n")

        tool = GrepTool(tmpdir)
        result = await tool.execute({
            "pattern": "start.*end",
            "multiline": True,
            "output_mode": "content"
        })

        assert result["is_error"] is False
        assert "start" in result["content"]


@pytest.mark.asyncio
async def test_grep_head_limit():
    """Test 10: Limit output with head_limit"""
    with tempfile.TemporaryDirectory() as tmpdir:
        for i in range(10):
            file = os.path.join(tmpdir, f"file{i}.txt")
            with open(file, "w") as f:
                f.write("match\n")

        tool = GrepTool(tmpdir)
        result = await tool.execute({
            "pattern": "match",
            "output_mode": "files_with_matches",
            "head_limit": 3
        })

        assert result["is_error"] is False
        lines = result["content"].strip().split("\n")
        assert len(lines) == 3
