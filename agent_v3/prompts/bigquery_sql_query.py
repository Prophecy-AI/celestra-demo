"""
Prompts for bigquery_sql_query tool - Execute SQL queries
"""


def get_orchestrator_info() -> str:
    """Return tool description for orchestrator system prompt"""
    return """- bigquery_sql_query: Execute SQL and get results
  Parameters: {"sql": "SQL query", "dataset_name": "descriptive_name"}"""


def get_system_prompt(**variables) -> None:
    """Non-LLM tool - no system prompt needed"""
    return None
