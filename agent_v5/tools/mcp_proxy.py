"""
MCP tool proxy for wrapping MCP server tools
"""
from typing import Dict, Callable, Any
from .base import BaseTool


class MCPToolProxy(BaseTool):
    """Proxy for MCP server tools"""

    def __init__(self, mcp_name: str, tool_name: str, tool_fn: Callable, mcp_schema: Dict, workspace_dir: str):
        super().__init__(workspace_dir)
        self.mcp_name = mcp_name
        self.tool_name = tool_name
        self.tool_fn = tool_fn
        self.mcp_schema = mcp_schema

    @property
    def name(self) -> str:
        return f"mcp__{self.mcp_name}__{self.tool_name}"

    @property
    def schema(self) -> Dict:
        return {
            "name": self.name,
            "description": self.mcp_schema.get("description", ""),
            "input_schema": self.mcp_schema.get("inputSchema", {})
        }

    async def execute(self, input: Dict) -> Dict:
        try:
            result = await self.tool_fn(input)

            if isinstance(result.get("content"), list):
                content_text = "\n".join([
                    block.get("text", "") for block in result["content"]
                    if block.get("type") == "text"
                ])
            else:
                content_text = str(result.get("content", ""))

            return {
                "content": content_text,
                "is_error": False
            }
        except Exception as e:
            return {
                "content": f"MCP tool error: {str(e)}",
                "is_error": True
            }
