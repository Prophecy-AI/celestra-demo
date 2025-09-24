"""
Main orchestration agent with improved state management
"""
import os
import sys
import re
import time
import json
import polars as pl
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from dotenv import load_dotenv
import anthropic

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.main_prompt import MAIN_AGENT_SYSTEM_PROMPT

from .context import SharedContext, TaskStatus
from .rx_claims_agent import RXClaimsAgent
from .med_claims_agent import MedClaimsAgent
from .colors import *
from .utils import debug_print

load_dotenv()

class MainAgent:
    def __init__(self):
        self.context = SharedContext()
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.session_id = time.strftime("%Y%m%d_%H%M%S")
        self.rx_agent = RXClaimsAgent(self.context, self.session_id)
        self.med_agent = MedClaimsAgent(self.context, self.session_id)
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.debug = os.getenv('DEBUG', '0') == '1'
        self.all_logs = []  # Store all logs for later saving
        self.api_calls = []  # Store all API calls for logging

    def log(self, message: str):
        """Colored debug logging"""
        timestamp_str = time.strftime('%H:%M:%S')

        # Store raw log with timestamp
        self.all_logs.append(f"[{timestamp_str}] [MAIN-AGENT] {message}")

        if self.debug:
            timestamp = f"{TIMESTAMP}[{timestamp_str}]{RESET}"

            # Color based on log content patterns
            if "ERROR" in message or "failed" in message.lower():
                color = ERROR
            elif "WARNING" in message:
                color = WARNING
            elif "SUCCESS" in message or "completed" in message or "Complete" in message:
                color = SUCCESS
            elif "PROCESS" in message or "Iteration" in message:
                color = PROCESS
            elif "PARSE" in message:
                color = CYAN
            elif "EXECUTE" in message:
                color = MAGENTA
            elif "LLM" in message:
                color = BRIGHT_BLUE
            elif "SQL" in message or "QUERY" in message:
                color = SQL
            elif "ANALYSIS" in message:
                color = BRIGHT_MAGENTA
            else:
                color = RESET

            print(f"{timestamp} {color}{message}{RESET}")

    def parse_agent_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse structured response from LLM"""
        actions = []

        self.log(f"[PARSE] Starting to parse response of length {len(response)}")
        self.log(f"[PARSE] First 500 chars of response: {response[:500]}...")

        # Parse different action types
        patterns = {
            "user_message": r'<user_message>(.*?)</user_message>',
            "rx_claims": r'<rx_claims_agent>(.*?)</rx_claims_agent>',
            "med_claims": r'<med_claims_agent>(.*?)</med_claims_agent>',
            "output": r'<output>(.*?)</output>'
        }

        for action_type, pattern in patterns.items():
            self.log(f"[PARSE] Looking for pattern '{action_type}' with regex: {pattern}")
            matches = re.findall(pattern, response, re.DOTALL)

            if matches:
                self.log(f"[PARSE] Found {len(matches)} match(es) for '{action_type}'")
                for i, match in enumerate(matches):
                    content = match.strip()
                    self.log(f"[PARSE] Match {i+1} for '{action_type}': {content[:100]}...")
                    actions.append({
                        "type": action_type,
                        "content": content
                    })
            else:
                self.log(f"[PARSE] No matches found for '{action_type}'")

        self.log(f"[PARSE] Total actions parsed: {len(actions)}")
        self.log(f"[PARSE] Action types found: {[a['type'] for a in actions]}")
        return actions

    def execute_actions(self, actions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Execute parsed actions with improved error handling"""
        self.log(f"[EXECUTE] Starting execution of {len(actions)} actions")

        results = {
            "messages": [],
            "data_collected": [],
            "errors": [],
            "completed": False
        }

        for idx, action in enumerate(actions):
            action_type = action["type"]
            content = action["content"]

            self.log(f"[EXECUTE] Processing action {idx+1}/{len(actions)}: type='{action_type}'")
            self.log(f"[EXECUTE] Action content: {content}")

            if action_type == "user_message":
                results["messages"].append(content)
                self.log(f"[EXECUTE-USER_MSG] Added message to results: {content[:100]}...")

            elif action_type == "rx_claims":
                task_id = f"rx_{len(self.context.tasks)}"
                self.log(f"[EXECUTE-RX] Creating task {task_id} with content: {content}")
                self.context.add_task(task_id, "rx_claims", content)
                future = self.executor.submit(self.rx_agent.execute, task_id, content)
                results["data_collected"].append({"task_id": task_id, "future": future})
                self.log(f"[EXECUTE-RX] Submitted RX claims task: {task_id}")

            elif action_type == "med_claims":
                task_id = f"med_{len(self.context.tasks)}"
                self.log(f"[EXECUTE-MED] Creating task {task_id} with content: {content}")
                self.context.add_task(task_id, "med_claims", content)
                future = self.executor.submit(self.med_agent.execute, task_id, content)
                results["data_collected"].append({"task_id": task_id, "future": future})
                self.log(f"[EXECUTE-MED] Submitted Med claims task: {task_id}")

            elif action_type == "output":
                results["messages"].append(content)
                results["completed"] = True
                self.log("[EXECUTE-OUTPUT] Workflow marked as complete")

        # Wait for data collection tasks to complete
        if results["data_collected"]:
            self.log(f"[EXECUTE-WAIT] Waiting for {len(results['data_collected'])} tasks to complete...")
            for item in results["data_collected"]:
                try:
                    self.log(f"[EXECUTE-WAIT] Waiting for task {item['task_id']}...")
                    result = item["future"].result(timeout=30)
                    self.log(f"[EXECUTE-WAIT] Task {item['task_id']} completed successfully")
                    self.log(f"[EXECUTE-WAIT] Result type: {type(result)}, Result: {str(result)}")
                except Exception as e:
                    error_msg = f"Task {item['task_id']} failed: {str(e)}"
                    results["errors"].append(error_msg)
                    self.log(f"[EXECUTE-WAIT-ERROR] {error_msg}")

        self.log(f"[EXECUTE] Execution complete. Messages: {len(results['messages'])}, Errors: {len(results['errors'])}, Completed: {results['completed']}")
        return results


    def process_request(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """Process a user request with iterative execution"""
        self.log(f"[PROCESS] Starting to process request: {user_input[:100]}...")
        self.context.conversation_history.append({"role": "user", "content": user_input})

        all_responses = []
        all_results = {"messages": [], "errors": [], "completed": False}
        max_iterations = 5
        iteration = 0

        while iteration < max_iterations and not all_results["completed"]:
            iteration += 1
            self.log(f"[PROCESS] Iteration {iteration}/{max_iterations}")

            try:
                # Get LLM response
                response = self.anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=MAIN_AGENT_SYSTEM_PROMPT,
                    messages=self.context.conversation_history,
                    temperature=0
                )

                # Extract text content from response (skip thinking blocks)
                agent_response = ""
                for block in response.content:
                    if hasattr(block, 'type'):
                        if block.type == 'thinking':
                            self.log(f"[PROCESS-THINKING] Model thinking: {block.thinking[:200]}...")
                        elif block.type == 'text':
                            agent_response += block.text
                    else:
                        # Fallback for simple text response
                        agent_response = block.text if hasattr(block, 'text') else str(block)

                self.log(f"[PROCESS] Got response: {len(agent_response)} chars")

                # Parse and execute
                actions = self.parse_agent_response(agent_response)
                if not actions:
                    self.log(f"[PROCESS] No actions found, stopping")
                    break

                results = self.execute_actions(actions)

                # Accumulate results
                all_responses.append(agent_response)
                all_results["messages"].extend(results.get("messages", []))
                all_results["errors"].extend(results.get("errors", []))
                all_results["completed"] = results.get("completed", False)

                # Add to conversation history
                self.context.conversation_history.append({"role": "assistant", "content": agent_response})

                # Continue if data collected but not done
                if results.get("data_collected") and not all_results["completed"]:
                    data_info = []
                    for key, df in self.context.dataframes.items():
                        data_info.append(f"{key}: {len(df)} rows" if not df.is_empty() else f"{key}: EMPTY")
                    prompt = f"Data collected: {data_info}. Continue with your plan or use <output> to finish."
                    self.context.conversation_history.append({"role": "user", "content": prompt})
                    self.log(f"[PROCESS] Prompting to continue with collected data")
                elif not results.get("data_collected") and not all_results["completed"]:
                    self.log(f"[PROCESS] No new data and not complete, stopping")
                    break

            except Exception as e:
                self.log(f"[PROCESS-ERROR] {str(e)}")
                all_results["errors"].append(str(e))
                break

        # Create summary
        summary = self.context.get_summary()
        summary["results"] = all_results
        summary["iterations"] = iteration

        combined_response = "\n\n".join(all_responses)
        self.log(f"[PROCESS] Complete after {iteration} iterations")
        return combined_response, summary

    def run_interactive(self):
        """Interactive chat loop with better state visibility"""
        print("Multi-Agent System v2 - Improved State Management")
        print("Type 'status' to see current state, 'quit' to exit")
        print("-" * 50)

        while True:
            try:
                user_input = input("\nYou: ").strip()

                if user_input.lower() == 'quit':
                    break

                if user_input.lower() == 'status':
                    summary = self.context.get_summary()
                    print(f"\nSystem Status:")
                    print(f"  Tasks: {summary['total_tasks']} total")
                    print(f"    Completed: {summary['completed']}")
                    print(f"    Failed: {summary['failed']}")
                    print(f"    Running: {summary['running']}")
                    print(f"    Pending: {summary['pending']}")
                    print(f"  DataFrames: {', '.join(summary['dataframes'])}")
                    print(f"  Errors: {summary['errors']}")
                    continue

                # Process request
                print("\nProcessing...", end="", flush=True)
                response, summary = self.process_request(user_input)
                print(" Complete")

                # Format and display response
                display_response = self._format_for_display(response)
                print(f"\n{display_response}")

                # Show results summary if tasks were executed
                if summary.get("total_tasks", 0) > 0:
                    print(f"\nResults Summary:")
                    print(f"  Tasks: {summary.get('completed', 0)} completed, {summary.get('failed', 0)} failed")

                    # Show DataFrame results
                    if summary.get('dataframes'):
                        for df_name in summary['dataframes']:
                            df = self.context.dataframes[df_name]
                            if df.is_empty():
                                print(f"  {df_name}: No data found")
                            else:
                                print(f"  {df_name}: {len(df)} rows")

                # Show any errors
                if summary.get("results", {}).get("errors"):
                    print(f"\nErrors occurred:")
                    for error in summary["results"]["errors"]:
                        print(f"  - {error}")

                # Check if workflow is complete
                if summary.get("results", {}).get("completed"):
                    print("\n✓ Workflow completed")
                    self.save_results()
                    break

            except KeyboardInterrupt:
                print("\n\nInterrupted by user")
                break
            except Exception as e:
                print(f"\nError: {str(e)}")

    def _format_for_display(self, response: str) -> str:
        """Format agent response for clean user display"""

        # Replace agent calls with status messages
        response = re.sub(r'<rx_claims_agent>.*?</rx_claims_agent>',
                         '[Querying prescription data...]', response, flags=re.DOTALL)
        response = re.sub(r'<med_claims_agent>.*?</med_claims_agent>',
                         '[Querying medical claims...]', response, flags=re.DOTALL)

        # Extract user messages and output
        user_msg_match = re.search(r'<user_message>(.*?)</user_message>', response, re.DOTALL)
        output_match = re.search(r'<output>(.*?)</output>', response, re.DOTALL)

        # Build clean output
        clean_parts = []
        if user_msg_match:
            clean_parts.append(user_msg_match.group(1).strip())
        if output_match:
            clean_parts.append(output_match.group(1).strip())

        # If no recognizable content, return cleaned response
        if not clean_parts:
            return response.strip()

        return '\n\n'.join(clean_parts)

    def save_results(self):
        """Save session metadata and logs (CSVs are saved by sub-agents)"""
        output_dir = f"output/session_{self.session_id}"
        os.makedirs(output_dir, exist_ok=True)

        # Save context summary
        summary = self.context.get_summary()
        with open(f"{output_dir}/summary.json", "w") as f:
            json.dump(summary, f, indent=2, default=str)

        print(f"\nResults saved to {output_dir}/")

def main():
    agent = MainAgent()
    agent.run_interactive()

if __name__ == "__main__":
    main()