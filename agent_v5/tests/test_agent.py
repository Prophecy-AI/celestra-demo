"""
Tests for ResearchAgent - uses real Anthropic API calls
"""
import pytest
import tempfile
import os
from agent_v5.agent import ResearchAgent


@pytest.mark.asyncio
async def test_agent_initialization():
    """Test 1: Agent initializes with tools"""
    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant."
        )

        assert agent.session_id == "test"
        assert agent.workspace_dir == tmpdir
        assert len(agent.tools.tools) == 10  # Bash, ReadBashOutput, KillShell, Read, Write, Edit, Glob, Grep, TodoWrite, DefineCohort
        assert "Bash" in agent.tools.tools
        assert "ReadBashOutput" in agent.tools.tools
        assert "KillShell" in agent.tools.tools
        assert "Read" in agent.tools.tools


@pytest.mark.asyncio
async def test_agent_simple_text_response():
    """Test 2: Agent handles simple text response without tools (real API call)"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant. Answer very briefly."
        )

        responses = []
        async for msg in agent.run("Say only the word 'hello' and nothing else"):
            responses.append(msg)

        text_deltas = [r for r in responses if r.get("type") == "text_delta"]
        assert len(text_deltas) > 0

        full_text = "".join([r["text"] for r in text_deltas])
        assert "hello" in full_text.lower()

        assert responses[-1]["type"] == "done"


@pytest.mark.asyncio
async def test_agent_streaming():
    """Test 3: Text chunks are yielded during streaming (real API call)"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant."
        )

        chunks = []
        async for msg in agent.run("Count to 3"):
            if msg.get("type") == "text_delta":
                chunks.append(msg["text"])

        assert len(chunks) > 0
        assert all(isinstance(chunk, str) for chunk in chunks)


@pytest.mark.asyncio
async def test_agent_conversation_history():
    """Test 4: Conversation history is maintained (real API call)"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant."
        )

        async for msg in agent.run("Say hi"):
            pass

        assert len(agent.conversation_history) == 2
        assert agent.conversation_history[0]["role"] == "user"
        assert agent.conversation_history[0]["content"] == "Say hi"
        assert agent.conversation_history[1]["role"] == "assistant"


@pytest.mark.asyncio
async def test_agent_tool_execution():
    """Test 5: Agent executes tool when requested (real API call)"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        test_file = os.path.join(tmpdir, "test.txt")
        with open(test_file, "w") as f:
            f.write("SECRET_CONTENT_12345\n")

        agent = ResearchAgent(
            session_id="test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant. You have access to file reading tools."
        )

        tool_executions = []
        async for msg in agent.run("Read the file test.txt"):
            if msg.get("type") == "tool_execution":
                tool_executions.append(msg)

        assert len(tool_executions) >= 1

        read_execution = [t for t in tool_executions if t["tool_name"] == "Read"]
        assert len(read_execution) == 1
        assert "SECRET_CONTENT_12345" in read_execution[0]["tool_output"]


@pytest.mark.asyncio
async def test_agent_bash_tool_execution():
    """Test 6: Agent executes Bash tool (real API call)"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant with bash access."
        )

        tool_executions = []
        async for msg in agent.run("Run the command: echo BASH_TEST_OUTPUT"):
            if msg.get("type") == "tool_execution":
                tool_executions.append(msg)

        bash_executions = [t for t in tool_executions if t["tool_name"] == "Bash"]
        assert len(bash_executions) >= 1
        assert "BASH_TEST_OUTPUT" in bash_executions[0]["tool_output"]


@pytest.mark.asyncio
async def test_agent_write_and_read():
    """Test 7: Agent writes and reads files (real API call)"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant with file access."
        )

        tool_executions = []
        async for msg in agent.run("Create a file called output.txt with the content 'UNIQUE_MARKER_99999' then read it back"):
            if msg.get("type") == "tool_execution":
                tool_executions.append(msg)

        write_tools = [t for t in tool_executions if t["tool_name"] == "Write"]
        read_tools = [t for t in tool_executions if t["tool_name"] == "Read"]

        assert len(write_tools) >= 1
        assert len(read_tools) >= 1
        assert "UNIQUE_MARKER_99999" in read_tools[0]["tool_output"]


@pytest.mark.asyncio
async def test_agent_registers_mcp_tools():
    """Test 8: Agent can register MCP tools via proxy"""
    with tempfile.TemporaryDirectory() as tmpdir:
        from agent_v5.tools.mcp_proxy import MCPToolProxy

        async def mock_mcp_tool(args):
            return {"content": "MCP result"}

        agent = ResearchAgent(
            session_id="test",
            workspace_dir=tmpdir,
            system_prompt="Test"
        )

        mcp_tool = MCPToolProxy(
            mcp_name="bigquery",
            tool_name="query",
            tool_fn=mock_mcp_tool,
            mcp_schema={"description": "Query BQ", "inputSchema": {}},
            workspace_dir=tmpdir
        )

        agent.tools.register(mcp_tool)

        assert "mcp__bigquery__query" in agent.tools.tools
        assert len(agent.tools.tools) == 11  # 10 core tools + 1 MCP tool
