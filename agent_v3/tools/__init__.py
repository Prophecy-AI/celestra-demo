"""
Tools package for agent_v3
"""
from .base import Tool, ToolResult
from .text_to_sql_rx import TextToSQLRx
from .text_to_sql_med import TextToSQLMed
from .text_to_sql_provider_payments import TextToSQLProviderPayments
from .text_to_sql_providers_bio import TextToSQLProvidersBio
from .bigquery_sql_query import BigQuerySQLQuery
from .communicate import Communicate
from .complete import Complete


def get_all_tools():
    """Return dictionary of all available tools"""
    return {
        "text_to_sql_rx": TextToSQLRx(),
        "text_to_sql_med": TextToSQLMed(),
        "text_to_sql_provider_payments": TextToSQLProviderPayments(),
        "text_to_sql_providers_bio": TextToSQLProvidersBio(),
        "bigquery_sql_query": BigQuerySQLQuery(),
        "communicate": Communicate(),
        "complete": Complete(),
    }


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
    "get_all_tools"
]
