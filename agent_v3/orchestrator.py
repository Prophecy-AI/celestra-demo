"""
Recursive orchestrator for agent_v3
"""
import time
from typing import Dict, Any, Optional
from .context import Context
from .llm_client import LLMClient
from .tools import get_all_tools
from .prompts.system_prompt import get_main_system_prompt
from .prompts import hints
from .exceptions import ConnectionLostError, ToolExecutionError, MaxRecursionError



class RecursiveOrchestrator:
    """Main orchestrator that manages the recursive flow"""

    def __init__(self, session_id: str, debug: bool = False, io_handler=None):
        self.session_id = session_id
        self.debug = debug
        self.context = Context(session_id, io_handler)
        self.llm_client = LLMClient()
        self.tools = get_all_tools()
        self.tool_names = list(self.tools.keys())
        self.io_handler = io_handler

    def log(self, message: str):
        """Debug logging"""
        if self.debug:
            timestamp = time.strftime('%H:%M:%S')
            print(f"[{timestamp}] [ORCHESTRATOR] {message}")

    def run(self, initial_input: str) -> Dict[str, Any]:
        """
        Main entry point for the recursive orchestrator.

        Args:
            initial_input: The user's initial request

        Returns:
            Dictionary with final results and context
        """
        self.log(f"Starting orchestration with input: {initial_input}")

        # Add initial user input to context
        self.context.add_user_message(initial_input)

        # Store original query for evaluations (if not already set)
        if not hasattr(self.context, 'original_user_query') or not self.context.original_user_query:
            self.context.original_user_query = initial_input

        try:
            # Start recursive loop
            result = self._recursive_loop()

            # Get final summary
            summary = self.context.get_summary()

            return {
                "success": result.get("completed", False),
                "summary": summary,
                "datasets": self.context.get_all_datasets(),
                "error": result.get("error")
            }
        except (ConnectionLostError, MaxRecursionError) as e:
            # These are terminal errors - return immediately
            self.log(f"Terminal error: {str(e)}")
            return {
                "success": False,
                "summary": self.context.get_summary(),
                "datasets": self.context.get_all_datasets(),
                "error": str(e)
            }

    def _recursive_loop(self, depth: int = 0) -> Dict[str, Any]:
        """
        Core recursive loop for tool execution.

        Args:
            depth: Current recursion depth

        Returns:
            Dictionary with completion status or error
        """
        # Check recursion depth
        if not self.context.increment_depth():
            self.log(f"Max recursion depth ({self.context.max_depth}) reached")
            raise MaxRecursionError(f"Maximum recursion depth ({self.context.max_depth}) reached")

        self.log(f"Recursion depth: {depth}")

        # Get messages for LLM
        messages = self.context.get_conversation_for_llm()

        # Add hints based on last tool execution
        self._add_contextual_hints()

        # Try to get tool selection from LLM
        max_force_attempts = 3
        force_attempts = 0
        tool_call = None

        while force_attempts < max_force_attempts:
            if force_attempts > 0:
                self.log(f"Force attempt {force_attempts}/{max_force_attempts}")
                # Add forcing message
                force_msg = self.llm_client.create_force_message(self.tool_names)
                messages.append({"role": "user", "content": f"<system-reminder>\n{force_msg}\n</system-reminder>"})

            # Call LLM
            self.log("Calling LLM for tool selection...")
            tool_call = self.llm_client.create_message(
                messages=messages,
                system_prompt=get_main_system_prompt(),
                available_tools=self.tool_names
            )

            if tool_call:
                self.log(f"LLM selected tool: {tool_call['tool']}")
                break

            force_attempts += 1
            self.log("No valid tool call found in LLM response")

        # Check if we got a valid tool call
        if not tool_call:
            error = "Failed to get valid tool selection from LLM after multiple attempts"
            self.log(f"ERROR: {error}")
            return {"completed": False, "error": error}

        # Execute the selected tool
        tool_name = tool_call["tool"]
        tool_params = tool_call.get("parameters", {})
        reasoning_trace = tool_call.get("reasoning_trace", "")

        # Stream the reasoning trace if available
        if reasoning_trace and self.io_handler:
            # Check if this is a WebSocket handler with reasoning trace support
            if hasattr(self.io_handler, 'send_reasoning_trace'):
                # Send reasoning trace as separate message type
                self.io_handler.send_reasoning_trace(reasoning_trace)
                self.log(f"Sent reasoning trace via WebSocket: {reasoning_trace[:50]}...")
            else:
                # Should not happen in WebSocket mode, but log it
                self.log(f"WARNING: No send_reasoning_trace method found on handler type: {type(self.io_handler)}")
        else:
            if not reasoning_trace:
                self.log(f"No reasoning trace found. Available keys: {list(tool_call.keys()) if tool_call else 'No tool_call'}")
            if not self.io_handler:
                self.log(f"No IO handler available")

        self.log(f"Executing tool: {tool_name} with params: {tool_params}")

        # Send action status based on tool type
        if self.io_handler and hasattr(self.io_handler, 'send_action_status'):
            if tool_name.startswith('text_to_sql'):
                action_map = {
                    'text_to_sql_rx': 'Generating SQL for prescription data',
                    'text_to_sql_med': 'Generating SQL for medical claims',
                    'text_to_sql_provider_payments': 'Generating SQL for provider payments',
                    'text_to_sql_providers_bio': 'Generating SQL for provider information'
                }
                self.io_handler.send_action_status("generating", action_map.get(tool_name, "Generating SQL query"))
            elif tool_name == 'bigquery_sql_query':
                dataset_name = tool_params.get('dataset_name', 'data')
                self.io_handler.send_action_status("querying", f"Querying database for: {dataset_name}")
            elif tool_name == 'complete':
                self.io_handler.send_action_status("completing", "Preparing final results")

        # Get the tool
        if tool_name not in self.tools:
            error = f"Unknown tool: {tool_name}"
            self.log(f"ERROR: {error}")
            self.context.add_tool_error(tool_name, tool_params, error)
            # Continue recursion to recover
            return self._recursive_loop(depth + 1)

        tool = self.tools[tool_name]

        # Execute tool
        try:
            result = tool.safe_execute(tool_params, self.context)

            # Add to context
            self.context.add_tool_execution(tool_name, tool_params, result)

            # Log execution
            if "error" in result:
                self.log(f"Tool execution error: {result['error']}")
            else:
                self.log(f"Tool executed successfully")

        except ConnectionLostError as e:
            # Connection errors are non-recoverable - stop execution
            error = f"Connection lost: {str(e)}"
            self.log(f"ERROR: {error}")
            self.context.add_tool_error(tool_name, tool_params, error)
            return {"completed": False, "error": error}
        except Exception as e:
            error = f"Tool execution exception: {str(e)}"
            self.log(f"ERROR: {error}")
            self.context.add_tool_error(tool_name, tool_params, error)
            # Continue recursion to recover
            return self._recursive_loop(depth + 1)

        # Handle based on tool type
        if tool_name == "complete":
            # Check if user wants to continue or end
            action = result.get("action", "continue")
            if action == "end":
                self.log("User chose to end session")
                return {"completed": True}
            else:
                # User wants to continue
                user_feedback = result.get("feedback", "")
                if user_feedback:
                    self.log(f"User feedback: {user_feedback}")
                    self.context.add_user_message(user_feedback)
                # Continue recursion
                return self._recursive_loop(depth + 1)

        elif tool_name == "communicate":
            # Add user response and continue
            user_response = result.get("user_response", "")
            if user_response:
                self.context.add_user_message(user_response)
            return self._recursive_loop(depth + 1)

        else:
            # For all other tools, continue recursion
            return self._recursive_loop(depth + 1)

    def _add_contextual_hints(self):
        """
        Add hints based on the last tool execution.

        This method is now tool-agnostic - tools provide their own hints
        via get_success_hint() and get_error_hint() methods.
        """
        last_execution = self.context.get_last_tool_execution()
        if not last_execution:
            # First iteration - no hints needed
            return

        # Get the tool instance
        tool_name = last_execution.tool_name
        if tool_name not in self.tools:
            self.log(f"Warning: Tool '{tool_name}' not found for hint generation")
            return

        tool = self.tools[tool_name]

        # Ask the tool for its hint based on success or error
        if last_execution.error:
            hint = tool.get_error_hint(self.context)
        else:
            hint = tool.get_success_hint(self.context)

        # Add hint if provided
        if hint:
            self.context.add_system_hint(hint)
            self.log(f"Added hint from {tool_name}: {hint}")