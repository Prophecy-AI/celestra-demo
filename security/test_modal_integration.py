"""Integration tests for Modal security prehooks

These tests verify that security prehooks work correctly in Modal's environment.
Run with: modal run security/test_modal_integration.py
"""
import pytest
import tempfile
import os
from pathlib import Path


@pytest.mark.asyncio
async def test_modal_workspace_isolation():
    """Test 1: Modal session workspaces are isolated from each other"""
    from agent_v5.agent import ResearchAgent
    from security import create_path_validation_prehook

    # Simulate Modal's workspace structure
    with tempfile.TemporaryDirectory() as base_workspace:
        session1_dir = os.path.join(base_workspace, "session_001")
        session2_dir = os.path.join(base_workspace, "session_002")

        os.makedirs(session1_dir)
        os.makedirs(session2_dir)

        # Create agent for session 1
        agent1 = ResearchAgent(
            session_id="session_001",
            workspace_dir=session1_dir,
            system_prompt="test"
        )

        # Inject prehooks
        hook1 = create_path_validation_prehook(session1_dir)
        agent1.tools.set_prehook("Write", hook1)

        # Create file in session 1
        result = await agent1.tools.execute("Write", {
            "file_path": "test.txt",
            "content": "session 1 data"
        })

        assert result["is_error"] is False

        # Try to access session 2's workspace from session 1 - should fail
        session2_path = os.path.join(session2_dir, "test.txt")
        result = await agent1.tools.execute("Write", {
            "file_path": session2_path,
            "content": "malicious"
        })

        assert result["is_error"] is True
        assert "Access denied" in result["content"]


@pytest.mark.asyncio
async def test_modal_volume_escape_prevention():
    """Test 2: Cannot escape Modal volume with relative paths"""
    from agent_v5.agent import ResearchAgent
    from security import create_path_validation_prehook

    with tempfile.TemporaryDirectory() as workspace_root:
        session_dir = os.path.join(workspace_root, "workspace", "session_abc")
        os.makedirs(session_dir)

        agent = ResearchAgent(
            session_id="session_abc",
            workspace_dir=session_dir,
            system_prompt="test"
        )

        hook = create_path_validation_prehook(session_dir)
        agent.tools.set_prehook("Read", hook)
        agent.tools.set_prehook("Write", hook)

        # Try various escape attempts
        escape_attempts = [
            "../../../etc/passwd",
            "../../other_session/data.txt",
            "../workspace/different_session/secret.txt",
        ]

        for escape_path in escape_attempts:
            result = await agent.tools.execute("Read", {
                "file_path": escape_path
            })

            assert result["is_error"] is True
            assert "Access denied" in result["content"], f"Failed to block: {escape_path}"


@pytest.mark.asyncio
async def test_modal_absolute_path_restriction():
    """Test 3: Absolute paths outside workspace are blocked"""
    from agent_v5.agent import ResearchAgent
    from security import create_path_validation_prehook

    with tempfile.TemporaryDirectory() as workspace:
        agent = ResearchAgent(
            session_id="test_session",
            workspace_dir=workspace,
            system_prompt="test"
        )

        hook = create_path_validation_prehook(workspace)
        agent.tools.set_prehook("Write", hook)

        # Try to write to system directories
        system_paths = [
            "/tmp/malicious.txt",
            "/etc/passwd",
            "/root/.ssh/authorized_keys",
            "/workspace/other_session/data.txt",  # Even if looks like workspace
        ]

        for sys_path in system_paths:
            result = await agent.tools.execute("Write", {
                "file_path": sys_path,
                "content": "malicious"
            })

            assert result["is_error"] is True
            assert "Access denied" in result["content"]


@pytest.mark.asyncio
async def test_modal_nested_directories_allowed():
    """Test 4: Nested directories within workspace are allowed"""
    from agent_v5.agent import ResearchAgent
    from security import create_path_validation_prehook

    with tempfile.TemporaryDirectory() as workspace:
        agent = ResearchAgent(
            session_id="test_session",
            workspace_dir=workspace,
            system_prompt="test"
        )

        hook = create_path_validation_prehook(workspace)
        agent.tools.set_prehook("Write", hook)

        # Create deeply nested files
        nested_paths = [
            "data/raw/file1.csv",
            "data/processed/file2.csv",
            "outputs/visualizations/chart.png",
            "a/b/c/d/e/deep.txt",
        ]

        for nested_path in nested_paths:
            result = await agent.tools.execute("Write", {
                "file_path": nested_path,
                "content": "test data"
            })

            assert result["is_error"] is False
            assert "created successfully" in result["content"].lower()


@pytest.mark.asyncio
async def test_modal_prehook_injection_in_main():
    """Test 5: Verify prehooks are correctly injected as in main.py"""
    from agent_v5.agent import ResearchAgent
    from security import create_path_validation_prehook

    with tempfile.TemporaryDirectory() as session_dir:
        # Simulate exactly how main.py does it
        agent = ResearchAgent(
            session_id="test_abc",
            workspace_dir=session_dir,
            system_prompt="test"
        )

        # Inject security prehooks for filesystem tools (same as main.py)
        path_hook = create_path_validation_prehook(session_dir)
        agent.tools.set_prehook("Read", path_hook)
        agent.tools.set_prehook("Write", path_hook)
        agent.tools.set_prehook("Edit", path_hook)
        agent.tools.set_prehook("Glob", path_hook)
        agent.tools.set_prehook("Grep", path_hook)

        # Verify all tools have prehooks
        tools_with_prehooks = ["Read", "Write", "Edit", "Glob", "Grep"]
        for tool_name in tools_with_prehooks:
            tool = agent.tools.tools[tool_name]
            assert tool._custom_prehook is not None, f"{tool_name} missing prehook"

        # Verify Bash doesn't have prehook (by design)
        bash_tool = agent.tools.tools.get("Bash")
        if bash_tool:
            assert bash_tool._custom_prehook is None


@pytest.mark.asyncio
async def test_modal_volume_commit_safe():
    """Test 6: Ensure volume commits don't leak data between sessions"""
    from agent_v5.agent import ResearchAgent
    from security import create_path_validation_prehook

    with tempfile.TemporaryDirectory() as base:
        # Create two session directories
        session1 = os.path.join(base, "session_001")
        session2 = os.path.join(base, "session_002")
        os.makedirs(session1)
        os.makedirs(session2)

        # Agent 1 writes to its workspace
        agent1 = ResearchAgent("session_001", session1, "test")
        hook1 = create_path_validation_prehook(session1)
        agent1.tools.set_prehook("Write", hook1)

        result = await agent1.tools.execute("Write", {
            "file_path": "secret.txt",
            "content": "session 1 secret"
        })
        assert result["is_error"] is False

        # Agent 2 tries to read agent 1's file - should fail
        agent2 = ResearchAgent("session_002", session2, "test")
        hook2 = create_path_validation_prehook(session2)
        agent2.tools.set_prehook("Read", hook2)

        result = await agent2.tools.execute("Read", {
            "file_path": os.path.join(session1, "secret.txt")
        })
        assert result["is_error"] is True
        assert "Access denied" in result["content"]


@pytest.mark.asyncio
async def test_modal_symlink_escape_blocked():
    """Test 7: Symlinks to outside workspace are blocked (Modal container escape)"""
    from agent_v5.agent import ResearchAgent
    from security import create_path_validation_prehook

    with tempfile.TemporaryDirectory() as workspace:
        agent = ResearchAgent("test", workspace, "test")
        hook = create_path_validation_prehook(workspace)
        agent.tools.set_prehook("Read", hook)

        # Create symlink pointing outside workspace
        symlink_path = os.path.join(workspace, "escape_link")
        os.symlink("/etc", symlink_path)

        # Try to read through symlink
        result = await agent.tools.execute("Read", {
            "file_path": os.path.join(symlink_path, "passwd")
        })

        assert result["is_error"] is True
        assert "Access denied" in result["content"]


def test_modal_image_includes_security_module():
    """Test 8: Verify Modal image config includes security module"""
    # This test verifies main.py has correct add_local_python_source
    import main

    # Read main.py source to check image configuration
    import inspect
    source = inspect.getsource(main)

    assert '.add_local_python_source("security")' in source, \
        "Modal image must include security module"
    assert 'from security import create_path_validation_prehook' in source, \
        "main.py must import prehook factory"
    assert 'agent.tools.set_prehook' in source, \
        "main.py must inject prehooks"
