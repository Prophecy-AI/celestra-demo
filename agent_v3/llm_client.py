"""
LLM client with strict single tool calling enforcement
"""
import os
import json
import re
from typing import Dict, Any, List, Optional
import anthropic
from opentelemetry.instrumentation.anthropic import AnthropicInstrumentor
from agent_v3.prompts import hints

AnthropicInstrumentor().instrument()

# ANSI color codes for dimmed output
DIM = "\033[2m"
RESET = "\033[0m"
GREEN_DIM = "\033[2;32m"
RED_DIM = "\033[2;31m"

class LLMClient:
    """Client for interacting with Claude via Anthropic API"""

    def __init__(self):
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.model = "claude-sonnet-4-20250514"
        self.max_tokens = 16384
        self.temperature = 0
        self.debug = os.getenv("DEBUG") == "1"

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

            if self.debug:
                print(f"{DIM}\n" + "="*80)
                print("LLM RESPONSE (RAW)")
                print("="*80)
                print(content)
                print("="*80 + f"\n{RESET}")

            # Parse for tool call
            tool_call = self._extract_tool_call(content, available_tools)

            if self.debug:
                if tool_call:
                    print(f"{GREEN_DIM}PARSED TOOL CALL:")
                    print(f"   Tool: {tool_call.get('tool')}")
                    print(f"   Parameters: {json.dumps(tool_call.get('parameters', {}), indent=6)}")
                    reasoning = tool_call.get('reasoning_trace', 'N/A')
                    print(f"   Reasoning: {reasoning[:100]}{'...' if len(reasoning) > 100 else ''}{RESET}")
                else:
                    print(f"{RED_DIM}FAILED TO PARSE TOOL CALL")
                    print(f"   Available tools: {available_tools}{RESET}")
                print()

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

        # ATTEMPT 0: Extract content from <TOOL-CALL> tags if present
        tool_call_match = re.search(r'<TOOL-CALL>\s*(.*?)\s*</TOOL-CALL>', content, re.DOTALL)
        if tool_call_match:
            content = tool_call_match.group(1).strip()
            if self.debug:
                print(f"{DIM}PARSING ATTEMPT 0: Extracted content from <TOOL-CALL> tags")
                print(f"   Extracted {len(content)} chars{RESET}")
        elif self.debug:
            print(f"{DIM}PARSING ATTEMPT 0: No <TOOL-CALL> tags found (will try parsing anyway){RESET}")

        if self.debug:
            print(f"\n{DIM}PARSING ATTEMPT 1: Entire content as JSON{RESET}")

        # First, try to parse the entire content as JSON
        try:
            data = json.loads(content)
            if self._validate_tool_call(data, available_tools):
                if self.debug:
                    print(f"{GREEN_DIM}   Success: Entire content is valid JSON tool call{RESET}")
                return data
            elif self.debug:
                print(f"{DIM}   Parsed as JSON but validation failed (tool: {data.get('tool', 'N/A')}){RESET}")
        except json.JSONDecodeError as e:
            if self.debug:
                print(f"{DIM}   Not valid JSON: {str(e)[:100]}{RESET}")

        if self.debug:
            print(f"\n{DIM}PARSING ATTEMPT 2: Extract JSON from content (regex){RESET}")

        # Try to find JSON within the content
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        matches = re.findall(json_pattern, content, re.DOTALL)

        if self.debug:
            print(f"{DIM}   Found {len(matches)} potential JSON blocks{RESET}")

        # STRICT VALIDATION: Count valid tool calls
        valid_tool_calls = []
        for i, match in enumerate(matches):
            try:
                data = json.loads(match)
                if self._validate_tool_call(data, available_tools):
                    valid_tool_calls.append((i+1, data))
                    if self.debug:
                        print(f"{GREEN_DIM}   Match {i+1} is valid tool call{RESET}")
                elif self.debug:
                    print(f"{DIM}   Match {i+1} parsed but validation failed (tool: {data.get('tool', 'N/A')}){RESET}")
            except json.JSONDecodeError:
                if self.debug:
                    print(f"{DIM}   Match {i+1} not valid JSON{RESET}")
                continue

        # CRITICAL: Reject if multiple valid tool calls found
        if len(valid_tool_calls) > 1:
            if self.debug:
                print(f"\n{RED_DIM}CRITICAL ERROR: Found {len(valid_tool_calls)} valid tool calls in one response!")
                print(f"   System requires EXACTLY ONE tool call per response.")
                print(f"   Tool calls found:")
                for match_num, data in valid_tool_calls:
                    print(f"      Match {match_num}: {data.get('tool')}")
                print(f"   This response will be REJECTED to enforce single-tool rule.{RESET}")
            return None

        # Return the single valid tool call if found
        if len(valid_tool_calls) == 1:
            return valid_tool_calls[0][1]

        if self.debug:
            print(f"\n{DIM}PARSING ATTEMPT 3: Manual extraction (tool + parameters regex){RESET}")

        # Try to extract tool name and parameters manually
        tool_match = re.search(r'"tool"\s*:\s*"([^"]+)"', content)
        params_match = re.search(r'"parameters"\s*:\s*(\{[^}]+\})', content)

        if tool_match:
            tool_name = tool_match.group(1)
            if self.debug:
                print(f"{DIM}   Found tool name: {tool_name}")
                print(f"   Tool in available_tools? {tool_name in available_tools}{RESET}")
            if tool_name in available_tools:
                try:
                    parameters = json.loads(params_match.group(1)) if params_match else {}
                    if self.debug:
                        print(f"{GREEN_DIM}   Manually extracted valid tool call{RESET}")
                    return {
                        "tool": tool_name,
                        "parameters": parameters
                    }
                except json.JSONDecodeError as e:
                    if self.debug:
                        print(f"{RED_DIM}   Parameters JSON invalid: {str(e)}{RESET}")
        elif self.debug:
            print(f"{DIM}   No tool field found{RESET}")

        if self.debug:
            print(f"\n{RED_DIM}ALL PARSING ATTEMPTS FAILED\n{RESET}")

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
        return hints.get_force_tool_selection_message(available_tools)