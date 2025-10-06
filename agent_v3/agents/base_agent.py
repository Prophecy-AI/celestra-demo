"""
Base agent class for specialized agent implementations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from ..llm_client import LLMClient
from ..context import Context


class BaseAgent(ABC):
    """Base class for all specialized agents"""

    def __init__(self, name: str, description: str, allowed_tools: List[str] = None):
        self.name = name
        self.description = description
        self.allowed_tools = allowed_tools or []
        self.llm_client = LLMClient()

    @abstractmethod
    def get_system_prompt(self) -> str:
        """Get the system prompt for this agent"""
        pass

    @abstractmethod
    def process(self, input_data: Dict[str, Any], context: Context, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Process input and return results"""
        pass

    def validate_tool_access(self, tool_name: str) -> bool:
        """Check if agent has access to requested tool"""
        if not self.allowed_tools:  # No restrictions
            return True
        return tool_name in self.allowed_tools

    def create_structured_message(self, messages: List[Dict[str, Any]], schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create a structured message using the LLM client"""
        system_prompt = self.get_system_prompt()

        # Add schema enforcement if provided
        if schema:
            system_prompt += f"\n\nIMPORTANT: Your response MUST conform to this JSON schema:\n{schema}"

        return self.llm_client.create_message(
            messages=messages,
            system_prompt=system_prompt,
            available_tools=self.allowed_tools
        )

    def format_context_for_agent(self, context: Context) -> Dict[str, Any]:
        """Format context information for agent consumption"""
        return {
            "datasets": list(context.get_all_datasets().keys()),
            "last_tool_execution": context.get_last_tool_name(),
            "conversation_length": len(context.conversation_history),
            "has_errors": context.has_error()
        }