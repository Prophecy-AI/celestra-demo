"""
Tool categories for hint system
"""
from enum import Enum


class ToolCategory(Enum):
    """
    Categories for tools to enable proper hint generation.

    Each tool MUST declare its category to participate in the hint system.
    This makes the orchestrator tool-agnostic and prevents hardcoded tool names.
    """
    SQL_GENERATION = "sql_generation"  # Tools that generate SQL queries
    SQL_EXECUTION = "sql_execution"    # Tools that execute SQL queries
    COMMUNICATION = "communication"     # Tools that interact with user
    COMPLETION = "completion"           # Tools that finalize the session
    CODE_EXECUTION = "code_execution"   # Tools that execute code in sandbox
    FILE_MANAGEMENT = "file_management" # Tools that manage sandbox files
    OTHER = "other"                     # Catch-all for tools without specific hints
