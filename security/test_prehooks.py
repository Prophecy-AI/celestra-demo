"""Integration tests for prehook system"""
import pytest
import tempfile
import os
from agent_v5.tools.registry import ToolRegistry
from agent_v5.tools.read import ReadTool
from agent_v5.tools.write import WriteTool
from security import create_path_validation_prehook, SecurityError


@pytest.mark.asyncio
async def test_prehook_validates_path():
    """Test 1: Prehook validates and normalizes paths"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(tmpdir)
        registry.register(ReadTool(tmpdir))

        # Inject prehook
        hook = create_path_validation_prehook(tmpdir)
        registry.set_prehook("Read", hook)

        # Create test file
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("hello")

        # Execute with relative path - should be normalized
        result = await registry.execute("Read", {"file_path": "test.txt"})

        assert result["is_error"] is False
        assert "hello" in result["content"]


@pytest.mark.asyncio
async def test_prehook_blocks_escape_attempts():
    """Test 2: Prehook blocks path escape attempts"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(tmpdir)
        registry.register(ReadTool(tmpdir))

        # Inject prehook
        hook = create_path_validation_prehook(tmpdir)
        registry.set_prehook("Read", hook)

        # Attempt to escape with ../
        result = await registry.execute("Read", {"file_path": "../../../etc/passwd"})

        assert result["is_error"] is True
        assert "Access denied" in result["content"]


@pytest.mark.asyncio
async def test_prehook_blocks_absolute_paths():
    """Test 3: Prehook blocks absolute paths outside workspace"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(tmpdir)
        registry.register(WriteTool(tmpdir))

        # Inject prehook
        hook = create_path_validation_prehook(tmpdir)
        registry.set_prehook("Write", hook)

        # Attempt to write to /etc
        result = await registry.execute("Write", {
            "file_path": "/etc/malicious.txt",
            "content": "bad"
        })

        assert result["is_error"] is True
        assert "Access denied" in result["content"]


@pytest.mark.asyncio
async def test_prehook_allows_nested_paths():
    """Test 4: Prehook allows nested paths within workspace"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(tmpdir)
        registry.register(WriteTool(tmpdir))

        # Inject prehook
        hook = create_path_validation_prehook(tmpdir)
        registry.set_prehook("Write", hook)

        # Write to nested path
        result = await registry.execute("Write", {
            "file_path": "a/b/c/test.txt",
            "content": "nested"
        })

        assert result["is_error"] is False
        assert "created successfully" in result["content"].lower()


@pytest.mark.asyncio
async def test_tool_without_prehook_works():
    """Test 5: Tool without prehook still works normally"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(tmpdir)
        registry.register(ReadTool(tmpdir))

        # NO prehook injected

        # Create test file
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("no prehook")

        # Execute normally
        result = await registry.execute("Read", {"file_path": test_file})

        assert result["is_error"] is False
        assert "no prehook" in result["content"]


@pytest.mark.asyncio
async def test_set_prehook_validates_tool_exists():
    """Test 6: set_prehook() raises error if tool doesn't exist"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(tmpdir)

        hook = create_path_validation_prehook(tmpdir)

        with pytest.raises(ValueError) as exc_info:
            registry.set_prehook("NonexistentTool", hook)

        assert "Tool not found" in str(exc_info.value)


@pytest.mark.asyncio
async def test_prehook_modifies_input_inplace():
    """Test 7: Prehook modifies input dict in-place (normalizes paths)"""
    with tempfile.TemporaryDirectory() as tmpdir:
        registry = ToolRegistry(tmpdir)
        registry.register(ReadTool(tmpdir))

        hook = create_path_validation_prehook(tmpdir)
        registry.set_prehook("Read", hook)

        # Create test file
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("test")

        # Input with relative path
        tool_input = {"file_path": "test.txt"}

        # Execute
        await registry.execute("Read", tool_input)

        # Input should be modified to absolute path (use realpath for comparison)
        assert tool_input["file_path"].startswith(os.path.realpath(tmpdir))
        assert tool_input["file_path"] == os.path.realpath(test_file)
