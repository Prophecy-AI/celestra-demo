"""
Base tool class for agent_v3
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, TYPE_CHECKING
from dataclasses import dataclass
import time
from agent_v3.exceptions import ConnectionLostError
from agent_v3.tools.categories import ToolCategory

if TYPE_CHECKING:
    from agent_v3.context import Context


@dataclass
class ToolResult:
    """Standardized tool result format"""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time: float = 0.0


class Tool(ABC):
    """
    Base class for all tools.

    IMPORTANT: All tools MUST specify a category for proper hint generation.
    This enables the orchestrator to be tool-agnostic.
    """

    def __init__(self, name: str, description: str, category: ToolCategory):
        self.name = name
        self.description = description
        self.category = category

    @classmethod
    @abstractmethod
    def get_orchestrator_info(cls) -> str:
        """Return tool description for orchestrator system prompt"""
        pass

    @classmethod
    def get_system_prompt(cls, **variables) -> Optional[str]:
        """
        Return system prompt for LLM-based tools.
        Non-LLM tools (like bigquery_sql_query) should return None.
        """
        return None

    @abstractmethod
    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Execute the tool with given parameters"""
        pass

    def validate_parameters(self, parameters: Dict[str, Any], required: list) -> Optional[str]:
        """Validate that required parameters are present"""
        missing = [param for param in required if param not in parameters]
        if missing:
            return f"Missing required parameters: {', '.join(missing)}"
        return None

    def safe_execute(self, parameters: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """
        Wrapper for safe execution with timing and error handling.
        Returns a dictionary suitable for LLM context.
        """
        start_time = time.time()

        try:
            result = self.execute(parameters, context)
            execution_time = time.time() - start_time

            if result.success:
                return {
                    **result.data,
                    "execution_time": execution_time
                }
            else:
                return {
                    "error": result.error or "Unknown error",
                    "execution_time": execution_time
                }

        except ConnectionLostError:
            # Don't catch connection errors - let them propagate up
            raise
        except Exception as e:
            return {
                "error": f"Tool execution failed: {str(e)}",
                "execution_time": time.time() - start_time
            }

    def get_success_hint(self, context: 'Context') -> Optional[str]:
        """
        Return a hint to guide the LLM after successful tool execution.

        Override this method in tool implementations to provide context-aware hints.
        Return None if no hint is needed.

        Args:
            context: Current execution context with conversation history and data

        Returns:
            Hint string or None
        """
        return None

    def get_error_hint(self, context: 'Context') -> Optional[str]:
        """
        Return a hint to guide the LLM after tool execution error.

        Override this method for custom error recovery hints.
        Default implementation returns a generic error handling hint.

        Args:
            context: Current execution context

        Returns:
            Hint string or None
        """
        from agent_v3.prompts import hints
        return hints.get_error_handling_hint()