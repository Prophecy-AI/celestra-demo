"""
Base tool class for agent_v3
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
import time
from agent_v3.exceptions import ConnectionLostError


@dataclass
class ToolResult:
    """Standardized tool result format"""
    success: bool
    data: Dict[str, Any]
    error: Optional[str] = None
    execution_time: float = 0.0


class Tool(ABC):
    """Base class for all tools"""

    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description

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