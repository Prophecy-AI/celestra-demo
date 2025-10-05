"""
Prompts for complete tool - Present final results to user
"""


def get_orchestrator_info() -> str:
    """Return tool description for orchestrator system prompt"""
    return """- complete: Present final results to user
  Parameters: {"summary": "brief conversational summary (2-3 sentences max)", "datasets": ["dataset1", "dataset2"]}"""


def get_system_prompt(**variables) -> None:
    """Non-LLM tool - no system prompt needed"""
    return None
