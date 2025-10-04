"""
Recursive orchestrator for agent_v3
"""
import time
from typing import Dict, Any, Optional
from .context import Context
from .llm_client import LLMClient
from .tools import get_all_tools
from .prompts.system_prompt import get_main_system_prompt
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

        # Check if this is the first iteration and if we should use multi-agent workflow
        if depth == 0 and hasattr(self.context, 'original_user_query'):
            user_query = self.context.original_user_query
            if user_query and self._should_use_multi_agent(user_query):
                self.log("Detected multi-agent workflow requirement")
                multi_agent_result = self._execute_multi_agent_workflow(user_query)

                if multi_agent_result.get("completed"):
                    return multi_agent_result
                else:
                    # Multi-agent workflow failed, continue with regular flow
                    self.log("Multi-agent workflow failed, continuing with regular flow")

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

        self.log(f"Executing tool: {tool_name} with params: {tool_params}")

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
        """Add hints based on the last tool execution"""
        last_tool = self.context.get_last_tool_name()

        if not last_tool:
            # First iteration - no hints needed
            return

        # If last tool was SQL generation, hint to execute it
        if last_tool in ["text_to_sql_rx", "text_to_sql_med", "text_to_sql_provider_payments", "text_to_sql_providers_bio"]:
            last_result = self.context.get_last_tool_result()
            if "sql" in last_result and not self.context.has_error():
                hint_msg = (
                    "SQL query has been generated. Use 'bigquery_sql_query' to execute it, "
                    "or call more tools IF NECESSARY to capture all the context needed from this or other datasets."
                )
                self.context.add_system_hint(hint_msg)
                self.log(f"Added hint: {hint_msg}")

        # If we have collected some data, hint about completion
        elif last_tool == "bigquery_sql_query":
            datasets = self.context.get_all_datasets()
            if datasets and not self.context.has_error():
                self.context.add_system_hint(
                    f"Query executed successfully. You have {len(datasets)} dataset(s). "
                    "Consider using 'complete' to present results, or continue with more queries if needed."
                )
                self.log("Added hint: Consider completion or more queries")

        # If there was an error, hint to communicate with user
        if self.context.has_error():
            self.context.add_system_hint(
                "The last tool execution had an error. Consider using 'communicate' "
                "to inform the user or try an alternative approach."
            )
            self.log("Added hint: Handle error condition")

    def _is_predictive_analysis_query(self, user_input: str) -> bool:
        """Detect if query requires predictive analysis workflow"""
        predictive_keywords = [
            "predict", "prediction", "predictive", "forecast", "high prescriber",
            "month 12", "early signals", "characteristics", "who will be",
            "identify prescribers", "trajectory", "patterns", "features"
        ]

        input_lower = user_input.lower()
        return any(keyword in input_lower for keyword in predictive_keywords)

    def _should_use_multi_agent(self, user_input: str) -> bool:
        """Determine if multi-agent workflow should be used"""
        # Use multi-agent for predictive analysis or complex analytical queries
        return (
            self._is_predictive_analysis_query(user_input) or
            any(keyword in user_input.lower() for keyword in [
                "comprehensive analysis", "detailed analysis", "multi-step",
                "feature engineering", "reason card", "evidence-based"
            ])
        )

    def _execute_multi_agent_workflow(self, user_input: str) -> Dict[str, Any]:
        """Execute multi-agent workflow for complex queries"""

        self.log("Executing multi-agent workflow")

        # Check if predictive_analysis tool is available
        if "predictive_analysis" not in self.tools:
            self.log("Predictive analysis tool not available, falling back to regular flow")
            return {"completed": False, "error": "Multi-agent workflow not available"}

        try:
            # Use predictive analysis tool to coordinate workflow
            tool = self.tools["predictive_analysis"]

            # Determine workflow type based on query
            workflow_type = "full"
            if "plan only" in user_input.lower() or "planning" in user_input.lower():
                workflow_type = "planning_only"

            parameters = {
                "query": user_input,
                "workflow_type": workflow_type,
                "validation_level": "standard"
            }

            self.log(f"Executing multi-agent workflow with parameters: {parameters}")

            # Execute the multi-agent workflow
            result = tool.safe_execute(parameters, self.context)

            # Add to context
            self.context.add_tool_execution("predictive_analysis", parameters, result)

            if "error" in result:
                self.log(f"Multi-agent workflow error: {result['error']}")
                return {"completed": False, "error": result["error"]}
            else:
                self.log("Multi-agent workflow completed successfully")

                # Check if we should present results or continue
                if result.get("final_output"):
                    # Multi-agent workflow produced final output, suggest completion
                    self.context.add_system_hint(
                        "Multi-agent predictive analysis completed successfully. "
                        "Consider using 'complete' to present the comprehensive results."
                    )

                return {"completed": True, "multi_agent_result": result}

        except Exception as e:
            error = f"Multi-agent workflow execution failed: {str(e)}"
            self.log(f"ERROR: {error}")
            return {"completed": False, "error": error}