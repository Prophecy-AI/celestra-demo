"""
Tool registry for dynamic tool discovery and loading
"""
import os
import importlib
from typing import Dict, Optional
from pathlib import Path
from .base import Tool


class ToolRegistry:
    """Registry for discovering and loading tools"""

    @staticmethod
    def get_all_tools() -> Dict[str, Tool]:
        """
        Scan and return all available tools

        Discovers tools by:
        1. Importing known tool modules
        2. Instantiating tool classes
        3. Returning a dictionary mapping tool_name -> Tool instance

        Returns:
            Dictionary of tool instances
        """
        tools = {}

        # Import SQL generation tools
        try:
            from .sql_generation import (
                TextToSQLRx,
                TextToSQLMed,
                TextToSQLProviderPayments,
                TextToSQLProvidersBio
            )

            tools["text_to_sql_rx"] = TextToSQLRx()
            tools["text_to_sql_med"] = TextToSQLMed()
            tools["text_to_sql_provider_payments"] = TextToSQLProviderPayments()
            tools["text_to_sql_providers_bio"] = TextToSQLProvidersBio()

        except ImportError as e:
            print(f"Warning: Failed to import SQL generation tools: {e}")

        # Import SQL execution tool
        try:
            from .sql_execution import BigQuerySQLQuery
            tools["bigquery_sql_query"] = BigQuerySQLQuery()
        except ImportError as e:
            print(f"Warning: Failed to import SQL execution tool: {e}")

        # Import IO tools
        try:
            from .io_tools import Communicate, Complete
            tools["communicate"] = Communicate()
            tools["complete"] = Complete()
        except ImportError as e:
            print(f"Warning: Failed to import IO tools: {e}")

        # TODO: Auto-discover generated tools
        # This will scan the tools directory for generated tools
        # and import them dynamically

        return tools

    @staticmethod
    def validate_tool(tool: Tool) -> Optional[str]:
        """
        Validate that a tool has the required structure

        Args:
            tool: Tool instance to validate

        Returns:
            Error message if invalid, None if valid
        """
        # Check if tool has required methods
        if not hasattr(tool, 'execute'):
            return "Tool missing 'execute' method"

        if not hasattr(tool, 'name'):
            return "Tool missing 'name' attribute"

        if not hasattr(tool, 'description'):
            return "Tool missing 'description' attribute"

        # Check if tool has a corresponding prompt file
        tool_name = tool.name
        prompts_dir = Path(__file__).parent.parent / "prompts" / "tools"
        prompt_file = prompts_dir / f"{tool_name}.yaml"

        # Only check for prompt file if this is a tool that needs one
        # (SQL generation tools, not IO tools)
        if tool_name.startswith("text_to_sql"):
            if not prompt_file.exists():
                return f"Prompt file not found: {prompt_file}"

        return None

    @staticmethod
    def list_tool_names() -> list[str]:
        """List all available tool names"""
        tools = ToolRegistry.get_all_tools()
        return list(tools.keys())

    @staticmethod
    def get_tool(tool_name: str) -> Optional[Tool]:
        """
        Get a specific tool by name

        Args:
            tool_name: Name of the tool

        Returns:
            Tool instance or None if not found
        """
        tools = ToolRegistry.get_all_tools()
        return tools.get(tool_name)
