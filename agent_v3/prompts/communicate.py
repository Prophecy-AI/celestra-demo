"""
Prompts for communicate tool - Ask user for clarification
"""


def get_orchestrator_info() -> str:
    """Return tool description for orchestrator system prompt"""
    return """- communicate: Ask user for clarification
  Parameters: {"message": "question or update for user (use markdown formatting when appropriate)"}"""


def get_system_prompt(**variables) -> None:
    """Non-LLM tool - no system prompt needed"""
    return None
