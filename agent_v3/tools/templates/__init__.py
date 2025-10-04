"""
Tool templates for generating new tools
"""
from .base_template import ToolTemplate
from .sql_tool_template import SQLToolTemplate

__all__ = ["ToolTemplate", "SQLToolTemplate"]
