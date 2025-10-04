"""
Recursive orchestrator for agent_v3
"""
import time
import asyncio
from typing import Dict, Any, Optional
from .context import Context
from .llm_client import LLMClient
from .tools import get_all_tools
from .prompts.system_prompt import get_main_system_prompt
from .exceptions import ConnectionLostError, ToolExecutionError, MaxRecursionError
from .agents.holistic_critic_agent import HolisticCriticAgent



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
        self.critic_agent = HolisticCriticAgent()  # Initialize holistic critic
        self.revision_attempted = False  # Track if revision has been attempted

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

            # CRITICAL: Run holistic critic evaluation BEFORE returning to user
            self.log("Running holistic critic evaluation before returning to user...")
            critique = self._run_holistic_critic_evaluation()

            # Check if revision is required
            if critique and critique.get("requires_revision") and critique.get("revision_priority") in ["critical", "high"]:
                self.log(f"Critic requires revision: {critique.get('revision_priority')}")

                # Add critique feedback to context for revision
                revision_result = self._handle_revision_feedback(critique)

                # Update result with revision outcome
                result = revision_result if revision_result.get("completed") else result

            # Get final summary
            summary = self.context.get_summary()

            return {
                "success": result.get("completed", False),
                "summary": summary,
                "datasets": self.context.get_all_datasets(),
                "error": result.get("error"),
                "critique": critique  # Include critique in response
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
            "identify", "trajectory", "patterns", "features"
        ]

        input_lower = user_input.lower()

        # Check for predictive keywords combined with prescribing/signals context
        has_predictive_keyword = any(keyword in input_lower for keyword in predictive_keywords)
        has_prescribing_context = any(word in input_lower for word in ["prescrib", "signal", "month"])

        # If it has both predictive keywords and prescribing context, it's likely predictive
        if has_predictive_keyword and has_prescribing_context:
            return True

        # Also check for direct predictive phrases
        return any(keyword in input_lower for keyword in ["predict", "prediction", "predictive", "forecast"])

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

    def _run_holistic_critic_evaluation(self) -> Optional[Dict[str, Any]]:
        """
        Run holistic critic evaluation on entire workflow.
        Returns critique or None if evaluation fails.
        """
        try:
            # Get full execution log
            execution_log = self.context.get_full_execution_log()

            self.log(f"Critic evaluating {len(execution_log.get('tool_executions', []))} tool executions")

            # Run async evaluation
            critique = asyncio.run(
                self.critic_agent.evaluate_workflow(execution_log)
            )

            self.log(f"Critic evaluation complete: overall_quality={critique.get('overall_quality_score', 'N/A')}, "
                    f"requires_revision={critique.get('requires_revision', False)}")

            return critique

        except Exception as e:
            self.log(f"Critic evaluation failed: {str(e)}")
            # Don't fail the entire workflow if critique fails
            return None

    def _handle_revision_feedback(self, critique: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle revision feedback from critic.
        Adds critique to context and triggers one revision attempt.

        Args:
            critique: Critique from HolisticCriticAgent

        Returns:
            Revision result
        """
        # Only allow one revision attempt to avoid infinite loops
        if self.revision_attempted:
            self.log("Revision already attempted once, skipping further revisions")
            return {"completed": False, "error": "Max revisions reached"}

        self.revision_attempted = True

        # Extract specific improvement suggestions
        critical_issues = critique.get("critical_issues", [])
        improvement_suggestions = critique.get("improvement_suggestions", [])
        missing_elements = critique.get("missing_elements", [])

        # Build revision prompt
        revision_prompt = "QUALITY ASSURANCE FEEDBACK - REVISION REQUIRED:\n\n"
        revision_prompt += f"Overall Quality Score: {critique.get('overall_quality_score', 'N/A')}\n"
        revision_prompt += f"Revision Priority: {critique.get('revision_priority', 'unknown')}\n\n"

        if critical_issues:
            revision_prompt += "CRITICAL ISSUES TO ADDRESS:\n"
            for issue in critical_issues[:3]:  # Limit to top 3
                revision_prompt += f"- {issue}\n"
            revision_prompt += "\n"

        if improvement_suggestions:
            revision_prompt += "IMPROVEMENT SUGGESTIONS:\n"
            for suggestion in improvement_suggestions[:5]:  # Limit to top 5
                revision_prompt += f"- {suggestion}\n"
            revision_prompt += "\n"

        if missing_elements:
            revision_prompt += "MISSING ELEMENTS:\n"
            for element in missing_elements[:3]:
                revision_prompt += f"- {element}\n"
            revision_prompt += "\n"

        revision_prompt += "Please revise your approach to address these issues and improve the analysis quality."

        # Add revision prompt as system hint
        self.context.add_system_hint(revision_prompt)
        self.log("Added revision feedback to context, continuing with improved strategy")

        # Continue recursion with feedback
        try:
            revision_result = self._recursive_loop(depth=0)
            return revision_result
        except Exception as e:
            self.log(f"Revision attempt failed: {str(e)}")
            return {"completed": False, "error": f"Revision failed: {str(e)}"}