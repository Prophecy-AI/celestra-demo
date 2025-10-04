"""
Tools package for agent_v3
"""
from .sql_generation import TextToSQLRx, TextToSQLMed, TextToSQLProvidersBio, TextToSQLProviderPayments
from .sql_execution import BigQuerySQLQuery
from .io_tools import Communicate, Complete
from .base import Tool, ToolResult
from .registry import ToolRegistry
from .generator import ToolGenerator

# Initialize all tools using the registry
def get_all_tools():
    """Return dictionary of all available tools (uses ToolRegistry)"""
    return ToolRegistry.get_all_tools()

__all__ = [
    "TextToSQLRx",
    "TextToSQLMed",
    "TextToSQLProviderPayments",
    "TextToSQLProvidersBio",
    "BigQuerySQLQuery",
    "Communicate",
    "Complete",
    "Tool",
    "ToolResult",
    "ToolRegistry",
    "ToolGenerator",
    "get_all_tools"
]