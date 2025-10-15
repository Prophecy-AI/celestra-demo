"""
Tests for MCP tool proxy
"""
import pytest
from agent_v5.tools.mcp_proxy import MCPToolProxy


async def mock_mcp_tool_simple(args):
    """Mock MCP tool that returns simple text"""
    return {
        "content": [
            {"type": "text", "text": f"Result: {args.get('query', 'none')}"}
        ]
    }


async def mock_mcp_tool_string(args):
    """Mock MCP tool that returns string content"""
    return {
        "content": f"String result: {args.get('value', 'none')}"
    }


async def mock_mcp_tool_error(args):
    """Mock MCP tool that raises error"""
    raise ValueError("Simulated MCP error")


@pytest.mark.asyncio
async def test_mcp_proxy_name_format():
    """Test 1: Verify naming convention mcp__{server}__{tool}"""
    schema = {
        "description": "Test tool",
        "inputSchema": {"type": "object"}
    }

    proxy = MCPToolProxy(
        mcp_name="testserver",
        tool_name="testtool",
        tool_fn=mock_mcp_tool_simple,
        mcp_schema=schema,
        workspace_dir="/workspace"
    )

    assert proxy.name == "mcp__testserver__testtool"


@pytest.mark.asyncio
async def test_mcp_proxy_schema_conversion():
    """Test 2: MCP schema converts to Anthropic format"""
    mcp_schema = {
        "description": "A test tool for testing",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string"}
            },
            "required": ["query"]
        }
    }

    proxy = MCPToolProxy(
        mcp_name="server",
        tool_name="tool",
        tool_fn=mock_mcp_tool_simple,
        mcp_schema=mcp_schema,
        workspace_dir="/workspace"
    )

    schema = proxy.schema

    assert schema["name"] == "mcp__server__tool"
    assert schema["description"] == "A test tool for testing"
    assert schema["input_schema"]["type"] == "object"
    assert "query" in schema["input_schema"]["properties"]


@pytest.mark.asyncio
async def test_mcp_proxy_execution():
    """Test 3: Execute mock MCP tool successfully"""
    schema = {"description": "Test", "inputSchema": {}}

    proxy = MCPToolProxy(
        mcp_name="server",
        tool_name="tool",
        tool_fn=mock_mcp_tool_simple,
        mcp_schema=schema,
        workspace_dir="/workspace"
    )

    result = await proxy.execute({"query": "test123"})

    assert result["is_error"] is False
    assert "Result: test123" in result["content"]


@pytest.mark.asyncio
async def test_mcp_proxy_response_format():
    """Test 4: Convert MCP response format to Anthropic format"""
    schema = {"description": "Test", "inputSchema": {}}

    proxy = MCPToolProxy(
        mcp_name="server",
        tool_name="tool",
        tool_fn=mock_mcp_tool_simple,
        mcp_schema=schema,
        workspace_dir="/workspace"
    )

    result = await proxy.execute({"query": "data"})

    assert isinstance(result, dict)
    assert "content" in result
    assert "is_error" in result
    assert isinstance(result["content"], str)


@pytest.mark.asyncio
async def test_mcp_proxy_error_handling():
    """Test 5: MCP tool error is caught and returned"""
    schema = {"description": "Test", "inputSchema": {}}

    proxy = MCPToolProxy(
        mcp_name="server",
        tool_name="errortool",
        tool_fn=mock_mcp_tool_error,
        mcp_schema=schema,
        workspace_dir="/workspace"
    )

    result = await proxy.execute({})

    assert result["is_error"] is True
    assert "MCP tool error" in result["content"]
    assert "Simulated MCP error" in result["content"]


@pytest.mark.asyncio
async def test_mcp_proxy_string_content():
    """Test 6: Handle MCP tools that return string content directly"""
    schema = {"description": "Test", "inputSchema": {}}

    proxy = MCPToolProxy(
        mcp_name="server",
        tool_name="stringtool",
        tool_fn=mock_mcp_tool_string,
        mcp_schema=schema,
        workspace_dir="/workspace"
    )

    result = await proxy.execute({"value": "abc"})

    assert result["is_error"] is False
    assert "String result: abc" in result["content"]


@pytest.mark.asyncio
async def test_mcp_proxy_multiple_content_blocks():
    """Test 7: Handle multiple content blocks from MCP tool"""
    async def multi_block_tool(args):
        return {
            "content": [
                {"type": "text", "text": "Block 1"},
                {"type": "text", "text": "Block 2"},
                {"type": "image", "data": "..."},  # Non-text block
                {"type": "text", "text": "Block 3"}
            ]
        }

    schema = {"description": "Test", "inputSchema": {}}

    proxy = MCPToolProxy(
        mcp_name="server",
        tool_name="multitool",
        tool_fn=multi_block_tool,
        mcp_schema=schema,
        workspace_dir="/workspace"
    )

    result = await proxy.execute({})

    assert result["is_error"] is False
    assert "Block 1" in result["content"]
    assert "Block 2" in result["content"]
    assert "Block 3" in result["content"]
