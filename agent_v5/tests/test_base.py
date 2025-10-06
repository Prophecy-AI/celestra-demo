"""
Tests for base tool framework (BaseTool and ToolRegistry)
"""
import pytest
from agent_v5.tools.base import BaseTool
from agent_v5.tools.registry import ToolRegistry


class MockTool(BaseTool):
    """Mock tool for testing"""

    @property
    def name(self) -> str:
        return "mock_tool"

    @property
    def schema(self) -> dict:
        return {
            "name": "mock_tool",
            "description": "A mock tool for testing",
            "input_schema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string"}
                },
                "required": ["message"]
            }
        }

    async def execute(self, input: dict) -> dict:
        return {
            "content": f"Mock: {input.get('message', 'no message')}",
            "is_error": False
        }


class ErrorMockTool(BaseTool):
    """Mock tool that returns errors"""

    @property
    def name(self) -> str:
        return "error_tool"

    @property
    def schema(self) -> dict:
        return {
            "name": "error_tool",
            "description": "A tool that returns errors",
            "input_schema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }

    async def execute(self, input: dict) -> dict:
        return {
            "content": "Error occurred",
            "is_error": True
        }


@pytest.mark.asyncio
async def test_base_tool_cannot_be_instantiated():
    """Test 1: BaseTool is abstract and cannot be instantiated"""
    with pytest.raises(TypeError):
        BaseTool("/workspace")


@pytest.mark.asyncio
async def test_mock_tool_can_be_registered():
    """Test 2: Mock tool can be registered in registry"""
    registry = ToolRegistry("/workspace")
    tool = MockTool("/workspace")

    registry.register(tool)

    assert "mock_tool" in registry.tools
    assert registry.tools["mock_tool"] == tool


@pytest.mark.asyncio
async def test_registry_returns_correct_schemas():
    """Test 3: Registry returns correct tool schemas"""
    registry = ToolRegistry("/workspace")
    tool1 = MockTool("/workspace")
    tool2 = ErrorMockTool("/workspace")

    registry.register(tool1)
    registry.register(tool2)

    schemas = registry.get_schemas()

    assert len(schemas) == 2
    assert any(s["name"] == "mock_tool" for s in schemas)
    assert any(s["name"] == "error_tool" for s in schemas)


@pytest.mark.asyncio
async def test_registry_executes_tool_correctly():
    """Test 4: Registry executes tool and returns correct result"""
    registry = ToolRegistry("/workspace")
    tool = MockTool("/workspace")
    registry.register(tool)

    result = await registry.execute("mock_tool", {"message": "hello"})

    assert result["content"] == "Mock: hello"
    assert result["is_error"] is False


@pytest.mark.asyncio
async def test_registry_handles_unknown_tool():
    """Test 5: Registry handles unknown tool gracefully"""
    registry = ToolRegistry("/workspace")

    result = await registry.execute("unknown_tool", {})

    assert "Unknown tool: unknown_tool" in result["content"]
    assert result["is_error"] is True


@pytest.mark.asyncio
async def test_tool_workspace_dir_is_set():
    """Test 6: Tool workspace_dir is correctly set"""
    tool = MockTool("/custom/workspace")

    assert tool.workspace_dir == "/custom/workspace"


@pytest.mark.asyncio
async def test_error_tool_returns_error():
    """Test 7: Tool can return error results"""
    registry = ToolRegistry("/workspace")
    tool = ErrorMockTool("/workspace")
    registry.register(tool)

    result = await registry.execute("error_tool", {})

    assert result["content"] == "Error occurred"
    assert result["is_error"] is True


@pytest.mark.asyncio
async def test_multiple_tools_registration():
    """Test 8: Multiple tools can be registered and executed"""
    registry = ToolRegistry("/workspace")
    tool1 = MockTool("/workspace")
    tool2 = ErrorMockTool("/workspace")

    registry.register(tool1)
    registry.register(tool2)

    result1 = await registry.execute("mock_tool", {"message": "test"})
    result2 = await registry.execute("error_tool", {})

    assert result1["is_error"] is False
    assert result2["is_error"] is True
    assert len(registry.tools) == 2
