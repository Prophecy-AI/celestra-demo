"""
Tools package for agent_v3
"""
from .sql_generation import TextToSQLRx, TextToSQLMed
from .sql_execution import BigQuerySQLQuery
from .io_tools import Communicate, Complete
from .base import Tool, ToolResult

# Initialize all tools
def get_all_tools():
    """Return dictionary of all available tools"""
    tools = {
        "text_to_sql_rx": TextToSQLRx(),
        "text_to_sql_med": TextToSQLMed(),
        "bigquery_sql_query": BigQuerySQLQuery(),
        "communicate": Communicate(),
        "complete": Complete()
    }
    return tools

__all__ = [
    "TextToSQLRx",
    "TextToSQLMed",
    "BigQuerySQLQuery",
    "Communicate",
    "Complete",
    "Tool",
    "ToolResult",
    "get_all_tools"
]