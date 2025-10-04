"""
LLM client with strict single tool calling enforcement
"""
import os
import json
import re
from typing import Dict, Any, List, Optional
import anthropic
from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
 
AnthropicInstrumentor().instrument()

class LLMClient:
    """Client for interacting with Claude via Anthropic API"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 2048
        self.temperature = 0

    def create_message(
        self,
        messages: List[Dict[str, str]],
        system_prompt: str,
        available_tools: List[str]
    ) -> Dict[str, Any]:
        """
        Create a message with the LLM and extract single tool call.

        Returns:
            Dictionary with tool name and parameters, or None if no valid tool found
        """
        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                system=system_prompt,
                messages=messages
            )

            # Extract text content
            content = response.content[0].text if response.content else ""

            # Parse for tool call
            tool_call = self._extract_tool_call(content, available_tools)

            return tool_call

        except Exception as e:
            print(f"LLM Error: {str(e)}")
            return None

    def _extract_tool_call(self, content: str, available_tools: List[str]) -> Optional[Dict[str, Any]]:
        """
        Extract a single tool call from LLM response.
        Expects JSON format: {"tool": "tool_name", "parameters": {...}}
        """
        # Try to find JSON in the response
        content = content.strip()

        # First, try to parse the entire content as JSON
        try:
            data = json.loads(content)
            if self._validate_tool_call(data, available_tools):
                return data
        except json.JSONDecodeError:
            pass

        # Try to find JSON within the content
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)

        for match in matches:
            try:
                data = json.loads(match)
                if self._validate_tool_call(data, available_tools):
                    return data
            except json.JSONDecodeError:
                continue

        # Try to extract tool name and parameters manually
        tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', content)
        params_match = re.search(r'"parameters"\s*:\s*(\{[^}]+\})', content)

        if tool_match:
            tool_name = tool_match.group(1)
            if tool_name in available_tools:
                try:
                    parameters = json.loads(params_match.group(1)) if params_match else {}
                    return {
                        "tool": tool_name,
                        "parameters": parameters
                    }
                except json.JSONDecodeError:
                    pass

        return None

    def _validate_tool_call(self, data: Dict[str, Any], available_tools: List[str]) -> bool:
        """Validate that the tool call is properly formatted"""
        if not isinstance(data, dict):
            return False

        if "tool" not in data:
            return False

        if data["tool"] not in available_tools:
            return False

        if "parameters" not in data:
            data["parameters"] = {}

        # reasoning_trace is optional but preferred
        if "reasoning_trace" not in data:
            data["reasoning_trace"] = ""

        return True

    def create_force_message(self, available_tools: List[str]) -> str:
        """Create a message that forces the LLM to select a tool"""
        return (
            f"You MUST select exactly ONE tool from the following list: {available_tools}\n"
            f"Respond with ONLY a JSON object in this format:\n"
            f'{{"tool": "<tool_name>", "parameters": {{"param1": "value1"}}, "reasoning_trace": "Brief explanation of your thinking"}}\n'
            f"Select the most appropriate tool for the current context."
        )