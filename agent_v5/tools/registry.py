"""
Tool registry for managing and executing tools
"""
from typing import Dict, List
from .base import BaseTool
from debug import log


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

    def set_prehook(self, tool_name: str, hook_fn) -> None:
        """
        Set custom prehook for a specific tool

        Args:
            tool_name: Name of tool to attach prehook to
            hook_fn: async function(input: Dict) -> None
        """
        if tool_name not in self.tools:
            raise ValueError(f"Tool not found: {tool_name}")

        self.tools[tool_name].set_custom_prehook(hook_fn)

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

        # Smart input logging - show primary param
        primary = next(iter(tool_input.values())) if tool_input else ""
        if isinstance(primary, str):
            primary = primary.replace("\n", "\\n")
        log(f"→ {tool_name}({primary})")

        # Run prehook for validation/normalization
        try:
            await self.tools[tool_name].prehook(tool_input)
        except Exception as e:
            log(f"✗ {tool_name} prehook: {e}", 2)
            return {"content": str(e), "is_error": True}

        result = await self.tools[tool_name].execute(tool_input)

        # Smart result logging - use debug_summary if provided, else fallback
        if result.get("is_error"):
            log(f"✗ {tool_name}: {str(result['content'])}", 2)
        else:
            summary = result.get("debug_summary") or f"ok"
            log(f"✓ {tool_name} {summary}", 1)

        return result
