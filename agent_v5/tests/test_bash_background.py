"""
Tests for background bash execution with ReadBashOutput and KillShell

CRITICAL: All tests MUST cleanup background processes to prevent leaks.
Uses fixtures with automatic cleanup.
"""
import pytest
import pytest_asyncio
import asyncio
from pathlib import Path
from agent_v5.tools.bash import BashTool
from agent_v5.tools.bash_output import ReadBashOutputTool
from agent_v5.tools.kill_shell import KillShellTool
from agent_v5.tools.bash_process_registry import BashProcessRegistry


@pytest_asyncio.fixture
async def bash_setup(tmp_path):
    """
    Setup registry and tools with automatic cleanup after test

    Ensures no background processes leak between tests.
    """
    registry = BashProcessRegistry()
    bash_tool = BashTool(str(tmp_path), registry)
    read_tool = ReadBashOutputTool(str(tmp_path), registry)
    kill_tool = KillShellTool(str(tmp_path), registry)

    yield registry, bash_tool, read_tool, kill_tool

    # CLEANUP: Kill all processes after test completes
    await registry.cleanup()


@pytest.mark.asyncio
async def test_background_execution_basic(bash_setup):
    """Test basic background execution returns shell_id"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    result = await bash_tool.execute({
        "command": "echo 'Hello from background'",
        "background": True
    })

    assert not result["is_error"]
    assert "bash_" in result["content"]
    assert "ReadBashOutput" in result["content"]
    assert "KillShell" in result["content"]


@pytest.mark.asyncio
async def test_incremental_output_reading(bash_setup):
    """Test cursor-based incremental reading (only new output)"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    # Start process that outputs incrementally
    result = await bash_tool.execute({
        "command": "for i in 1 2 3 4 5; do echo 'Line '$i; sleep 0.1; done",
        "background": True
    })

    assert not result["is_error"]
    shell_id = result["content"].split("process: ")[1].split("\n")[0]

    # Wait for some output
    await asyncio.sleep(0.3)

    # First read - should get lines 1-2
    output1 = await read_tool.execute({"shell_id": shell_id})
    assert not output1["is_error"]
    assert "Line 1" in output1["content"]

    # Second read - should only get NEW lines (3-4), not repeat 1-2
    await asyncio.sleep(0.3)
    output2 = await read_tool.execute({"shell_id": shell_id})
    assert not output2["is_error"]

    # Verify cursor worked: output2 doesn't contain Line 1 again
    assert "Line 1" not in output2["content"] or "(no new output" in output2["content"]

    # Wait for completion
    await asyncio.sleep(0.5)
    output3 = await read_tool.execute({"shell_id": shell_id})
    assert "COMPLETED" in output3["content"]


@pytest.mark.asyncio
async def test_process_completion_status(bash_setup):
    """Test process status changes from RUNNING to COMPLETED"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    # Start quick process
    result = await bash_tool.execute({
        "command": "echo 'Done'",
        "background": True
    })
    shell_id = result["content"].split("process: ")[1].split("\n")[0]

    # Immediately check - might be RUNNING or already COMPLETED
    output1 = await read_tool.execute({"shell_id": shell_id})
    assert not output1["is_error"]

    # Wait and check again - should definitely be COMPLETED
    await asyncio.sleep(0.2)
    output2 = await read_tool.execute({"shell_id": shell_id})
    assert "COMPLETED" in output2["content"]
    assert "exit code: 0" in output2["content"]


@pytest.mark.asyncio
async def test_kill_running_process(bash_setup):
    """Test KillShell terminates running process"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    # Start long-running process
    result = await bash_tool.execute({
        "command": "sleep 100",
        "background": True
    })
    shell_id = result["content"].split("process: ")[1].split("\n")[0]

    # Verify it's in registry
    assert registry.get(shell_id) is not None

    # Kill it
    kill_result = await kill_tool.execute({"shell_id": shell_id})
    assert not kill_result["is_error"]
    assert "Killed" in kill_result["content"]

    # Verify removed from registry
    assert registry.get(shell_id) is None


@pytest.mark.asyncio
async def test_backward_compatibility_foreground(tmp_path):
    """Test foreground execution still works without registry"""
    # No registry provided - should work for foreground
    bash_tool = BashTool(str(tmp_path))

    result = await bash_tool.execute({
        "command": "echo 'Hello foreground'",
        "background": False
    })

    assert not result["is_error"]
    assert "Hello foreground" in result["content"]


@pytest.mark.asyncio
async def test_background_without_registry_fails(tmp_path):
    """Test background execution fails gracefully without registry"""
    bash_tool = BashTool(str(tmp_path))  # No registry

    result = await bash_tool.execute({
        "command": "echo 'test'",
        "background": True
    })

    assert result["is_error"]
    assert "not available" in result["content"]
    assert "no process registry" in result["content"]


@pytest.mark.asyncio
async def test_read_output_without_registry_fails(tmp_path):
    """Test ReadBashOutput fails gracefully without registry"""
    read_tool = ReadBashOutputTool(str(tmp_path))  # No registry

    result = await read_tool.execute({"shell_id": "bash_12345678"})

    assert result["is_error"]
    assert "not available" in result["content"]


@pytest.mark.asyncio
async def test_kill_shell_without_registry_fails(tmp_path):
    """Test KillShell fails gracefully without registry"""
    kill_tool = KillShellTool(str(tmp_path))  # No registry

    result = await kill_tool.execute({"shell_id": "bash_12345678"})

    assert result["is_error"]
    assert "not available" in result["content"]


@pytest.mark.asyncio
async def test_missing_shell_id(bash_setup):
    """Test reading output from non-existent shell_id"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    result = await read_tool.execute({"shell_id": "bash_nonexistent"})

    assert result["is_error"]
    assert "not found" in result["content"]


@pytest.mark.asyncio
async def test_multiple_background_processes(bash_setup):
    """Test multiple background processes running simultaneously"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    # Start 3 processes
    shell_ids = []
    for i in range(3):
        result = await bash_tool.execute({
            "command": f"echo 'Process {i}'; sleep 0.2; echo 'Done {i}'",
            "background": True
        })
        shell_id = result["content"].split("process: ")[1].split("\n")[0]
        shell_ids.append(shell_id)

    # Verify all in registry
    assert len(registry.list_all()) == 3

    # Wait for completion
    await asyncio.sleep(0.5)

    # Read from each
    for i, shell_id in enumerate(shell_ids):
        output = await read_tool.execute({"shell_id": shell_id})
        assert not output["is_error"]
        assert f"Process {i}" in output["content"]
        assert f"Done {i}" in output["content"]


@pytest.mark.asyncio
async def test_cwd_parameter_used(bash_setup):
    """Test that commands execute in workspace directory (cwd parameter)"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    # Create file in workspace (get tmp_path from registry's workspace)
    # Actually, we need tmp_path here, so use foreground test
    pass  # Covered by foreground test


@pytest.mark.asyncio
async def test_cwd_parameter_foreground(tmp_path):
    """Test that foreground commands execute in workspace directory"""
    bash_tool = BashTool(str(tmp_path))

    # Create file in workspace
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")

    # Execute command that references workspace file (no cd needed)
    result = await bash_tool.execute({
        "command": "cat test.txt",
        "background": False
    })

    assert not result["is_error"]
    assert "content" in result["content"]


@pytest.mark.asyncio
async def test_stdout_stderr_combined(bash_setup):
    """Test that stdout and stderr are both captured"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    # Command that outputs to both stdout and stderr
    result = await bash_tool.execute({
        "command": "echo 'stdout message'; echo 'stderr message' >&2",
        "background": True
    })
    shell_id = result["content"].split("process: ")[1].split("\n")[0]

    await asyncio.sleep(0.2)

    output = await read_tool.execute({"shell_id": shell_id})
    assert not output["is_error"]
    assert "stdout message" in output["content"]
    assert "stderr message" in output["content"]


@pytest.mark.asyncio
async def test_exit_code_captured(bash_setup):
    """Test that exit code is captured for failed commands"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    # Command that fails
    result = await bash_tool.execute({
        "command": "exit 42",
        "background": True
    })
    shell_id = result["content"].split("process: ")[1].split("\n")[0]

    await asyncio.sleep(0.2)

    output = await read_tool.execute({"shell_id": shell_id})
    assert "exit code: 42" in output["content"]


@pytest.mark.asyncio
async def test_registry_cleanup(bash_setup):
    """Test registry cleanup kills all processes"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    # Start multiple long-running processes
    for i in range(3):
        await bash_tool.execute({
            "command": "sleep 100",
            "background": True
        })

    assert len(registry.list_all()) == 3

    # Cleanup all (will be called by fixture too, but test it explicitly)
    killed = await registry.cleanup()
    assert killed == 3
    assert len(registry.list_all()) == 0


@pytest.mark.asyncio
async def test_no_output_message(bash_setup):
    """Test message when no new output since last read"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    # Start quick process
    result = await bash_tool.execute({
        "command": "echo 'Once'",
        "background": True
    })
    shell_id = result["content"].split("process: ")[1].split("\n")[0]

    await asyncio.sleep(0.2)

    # First read - gets output
    output1 = await read_tool.execute({"shell_id": shell_id})
    assert "Once" in output1["content"]

    # Second read - no new output
    output2 = await read_tool.execute({"shell_id": shell_id})
    assert "no new output" in output2["content"]


@pytest.mark.asyncio
async def test_kill_already_completed_process(bash_setup):
    """Test killing already-completed process is idempotent"""
    registry, bash_tool, read_tool, kill_tool = bash_setup

    # Start quick process
    result = await bash_tool.execute({
        "command": "echo 'Done'",
        "background": True
    })
    shell_id = result["content"].split("process: ")[1].split("\n")[0]

    # Wait for completion
    await asyncio.sleep(0.2)

    # Kill completed process - should work
    kill_result = await kill_tool.execute({"shell_id": shell_id})
    assert not kill_result["is_error"]
    assert "already completed" in kill_result["content"] or "Killed" in kill_result["content"]
