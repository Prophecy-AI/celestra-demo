"""
Tool registry for managing and executing tools
"""
from typing import Dict, List
from .base import BaseTool


class ToolRegistry:
    """Registry for managing tools and executing them"""

    def __init__(self, workspace_dir: str):
        """
        Initialize tool registry

        Args:
            workspace_dir: Path to workspace directory
        """
        self.workspace_dir = workspace_dir
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool) -> None:
        """
        Register a tool in the registry

        Args:
            tool: Tool instance to register
        """
        self.tools[tool.name] = tool

    def get_schemas(self) -> List[Dict]:
        """
        Get all tool schemas in Anthropic API format

        Returns:
            List of tool schema dicts
        """
        return [tool.schema for tool in self.tools.values()]

    async def execute(self, tool_name: str, tool_input: Dict) -> Dict:
        """
        Execute a tool by name

        Args:
            tool_name: Name of tool to execute
            tool_input: Tool input parameters

        Returns:
            Dict with content and is_error keys
        """
        if tool_name not in self.tools:
            return {
                "content": f"Unknown tool: {tool_name}",
                "is_error": True
            }

        return await self.tools[tool_name].execute(tool_input)
