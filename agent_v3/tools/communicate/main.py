"""
Communicate tool - Ask user for clarification or provide updates
"""
from typing import Dict, Any
from agent_v3.tools.base import Tool, ToolResult
from agent_v3.tools.categories import ToolCategory
from . import prompts


class Communicate(Tool):
    """Tool for communicating with the user"""

    def __init__(self):
        super().__init__(
            name="communicate",
            description="Ask user for clarification or provide intermediate updates",
            category=ToolCategory.COMMUNICATION
        )

    @classmethod
    def get_orchestrator_info(cls) -> str:
        """Return tool description for orchestrator system prompt"""
        return prompts.get_orchestrator_info()

    @classmethod
    def get_system_prompt(cls, **variables) -> None:
        """Non-LLM tool - no system prompt needed"""
        return prompts.get_system_prompt(**variables)

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Send message to user and get response"""
        error = self.validate_parameters(parameters, ["message"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        message = parameters["message"]
        io_handler = getattr(context, 'io_handler', None)

        output_msg = f"\n💬 Assistant: {message}"
        if io_handler:
            io_handler.send_output(output_msg)
        else:
            print(output_msg)

        try:
            if io_handler:
                user_response = io_handler.get_user_input("\n👤 You: ").strip()
            else:
                user_response = input("\n👤 You: ").strip()

            return ToolResult(
                success=True,
                data={"user_response": user_response}
            )
        except (KeyboardInterrupt, EOFError):
            return ToolResult(
                success=False,
                data={},
                error="User input interrupted"
            )
