"""
System hints and reminders for the orchestrator
All hardcoded prompts and hints centralized here for easy maintenance
"""
from typing import List


def get_force_tool_selection_message(available_tools: List[str]) -> str:
    """
    Create a message that forces the LLM to select a tool.
    Used when LLM fails to return a valid tool call.
    """
    return (
        f"You MUST select exactly ONE tool from the following list: {available_tools}\n"
        f"Respond with ONLY a JSON object in this format:\n"
        f'{{"tool": "<tool_name>", "parameters": {{"param1": "value1"}}, "reasoning_trace": "Brief explanation of your thinking"}}\n'
        f"Select the most appropriate tool for the current context."
    )


def get_sql_generated_hint() -> str:
    """
    Hint to use after SQL generation tools complete successfully.
    Suggests executing the SQL or gathering more context if needed.
    """
    return (
        "SQL query has been generated. Use 'bigquery_sql_query' to execute it, "
        "or call more tools IF NECESSARY to capture all the context needed from this or other datasets."
    )


def get_query_executed_hint(num_datasets: int) -> str:
    """
    Hint to use after BigQuery execution completes successfully.
    Suggests completing or continuing with more queries.

    Args:
        num_datasets: Number of datasets collected so far
    """
    return (
        f"Query executed successfully. You have {num_datasets} dataset(s). "
        "Consider using 'complete' to present results, or continue with more queries if needed."
    )


def get_error_handling_hint() -> str:
    """
    Hint to use when the last tool execution had an error.
    Suggests communicating with user or trying alternative approach.
    """
    return (
        "The last tool execution had an error. Consider using 'communicate' "
        "to inform the user or try an alternative approach."
    )


# Additional hints that might be useful for future extensions

def get_missing_parameters_hint(tool_name: str, missing_params: List[str]) -> str:
    """
    Hint when required parameters are missing from a tool call.

    Args:
        tool_name: Name of the tool with missing parameters
        missing_params: List of missing parameter names
    """
    params_str = ", ".join(missing_params)
    return (
        f"The '{tool_name}' tool requires the following missing parameters: {params_str}. "
        f"Please provide all required parameters or use 'communicate' to ask the user for clarification."
    )


def get_recursion_depth_warning(current_depth: int, max_depth: int) -> str:
    """
    Hint when approaching recursion depth limit.

    Args:
        current_depth: Current recursion depth
        max_depth: Maximum allowed depth
    """
    return (
        f"You are at recursion depth {current_depth} of {max_depth}. "
        f"Consider using 'complete' to finish the analysis or 'communicate' "
        f"to check if the user needs more information."
    )


def get_no_data_hint() -> str:
    """
    Hint when no data has been collected yet but completion is attempted.
    """
    return (
        "No datasets have been created yet. You should generate and execute SQL queries "
        "before using 'complete', or use 'communicate' to clarify the user's needs."
    )
