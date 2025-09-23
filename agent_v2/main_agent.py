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
from prompts.main_prompt import MAIN_AGENT_SYSTEM_PROMPT, ANALYSIS_PROMPT

from .context import SharedContext, TaskStatus
from .rx_claims_agent import RXClaimsAgent
from .med_claims_agent import MedClaimsAgent
from .utils import debug_print

load_dotenv()

class MainAgent:
    def __init__(self):
        self.context = SharedContext()
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.rx_agent = RXClaimsAgent(self.context)
        self.med_agent = MedClaimsAgent(self.context)
        self.executor = ThreadPoolExecutor(max_workers=3)
        self.session_id = time.strftime("%Y%m%d_%H%M%S")
        self.debug = os.getenv('DEBUG', '0') == '1'

    def log(self, message: str):
        """Simple logging with grey/dim color"""
        if self.debug:
            debug_print(f"[{time.strftime('%H:%M:%S')}] {message}")

    def parse_agent_response(self, response: str) -> List[Dict[str, Any]]:
        """Parse structured response from LLM"""
        actions = []

        self.log(f"[PARSE] Starting to parse response of length {len(response)}")
        self.log(f"[PARSE] First 500 chars of response: {response[:500]}...")

        # Parse different action types
        patterns = {
            "think": r'<think>(.*?)</think>',
            "user_message": r'<user_message>(.*?)</user_message>',
            "rx_claims": r'<rx_claims_agent>(.*?)</rx_claims_agent>',
            "med_claims": r'<med_claims_agent>(.*?)</med_claims_agent>',
            "analysis": r'<analysis>(.*?)</analysis>',
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
            self.log(f"[EXECUTE] Action content: {content[:200]}...")

            if action_type == "think":
                self.log(f"[EXECUTE-THINK] Processing thinking: {content[:100]}...")

            elif action_type == "user_message":
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

            elif action_type == "analysis":
                self.log(f"[EXECUTE-ANALYSIS] Starting analysis: {content[:100]}...")
                analysis_result = self.perform_analysis(content)
                results["messages"].append(f"Analysis result: {analysis_result}")
                self.log(f"[EXECUTE-ANALYSIS] Analysis completed")

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
                    self.log(f"[EXECUTE-WAIT] Result type: {type(result)}, Result: {str(result)[:200]}...")
                except Exception as e:
                    error_msg = f"Task {item['task_id']} failed: {str(e)}"
                    results["errors"].append(error_msg)
                    self.log(f"[EXECUTE-WAIT-ERROR] {error_msg}")

        self.log(f"[EXECUTE] Execution complete. Messages: {len(results['messages'])}, Errors: {len(results['errors'])}, Completed: {results['completed']}")
        return results

    def perform_analysis(self, request: str) -> str:
        """Perform analysis on collected data"""
        # Get all available dataframes
        available_dfs = []
        for key, df in self.context.dataframes.items():
            if isinstance(df, pl.DataFrame):
                available_dfs.append(f"{key}: {len(df)} rows, columns: {df.columns}")

        if not available_dfs:
            return "No data available for analysis"

        # Generate analysis code
        prompt = f"""Available DataFrames:
{chr(10).join(available_dfs)}

Analysis request: {request}

Generate Python code using Polars to perform this analysis.
The dataframes are available as: {', '.join(self.context.dataframes.keys())}
Store the final result in a variable called 'result'."""

        response = self.anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )

        code = response.content[0].text
        code_match = re.search(r'```python\n(.*?)\n```', code, re.DOTALL)
        if code_match:
            code = code_match.group(1)

        # Execute analysis
        try:
            local_vars = dict(self.context.dataframes)
            local_vars['pl'] = pl
            exec(code, {"__builtins__": __builtins__, "pl": pl}, local_vars)

            if 'result' in local_vars:
                result = local_vars['result']
                if isinstance(result, pl.DataFrame):
                    self.context.store_dataframe('analysis_result', result)
                    return f"Analysis completed: {len(result)} rows"
                return str(result)
            return "Analysis completed but no result found"

        except Exception as e:
            return f"Analysis failed: {str(e)}"

    def process_request(self, user_input: str) -> Tuple[str, Dict[str, Any]]:
        """Process a user request with improved state management"""
        self.log(f"[PROCESS] Starting to process request: {user_input[:100]}...")

        # Add to conversation history
        self.context.conversation_history.append({"role": "user", "content": user_input})
        self.log(f"[PROCESS] Added to conversation history. History length: {len(self.context.conversation_history)}")

        # Get LLM response
        try:
            self.log(f"[PROCESS-LLM] Calling Anthropic API with model claude-sonnet-4-20250514")
            self.log(f"[PROCESS-LLM] System prompt length: {len(MAIN_AGENT_SYSTEM_PROMPT)}")
            self.log(f"[PROCESS-LLM] Messages count: {len(self.context.conversation_history)}")

            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=MAIN_AGENT_SYSTEM_PROMPT,
                messages=self.context.conversation_history,
                temperature=0.1
            )

            agent_response = response.content[0].text
            self.log(f"[PROCESS-LLM] Got response of length {len(agent_response)}")
            self.log(f"[PROCESS-LLM] Response preview: {agent_response[:500]}...")

            self.context.conversation_history.append({"role": "assistant", "content": agent_response})
            self.log(f"[PROCESS-LLM] Added response to conversation history")

        except Exception as e:
            error_msg = f"LLM call failed: {str(e)}"
            self.log(f"[PROCESS-LLM-ERROR] {error_msg}")
            self.context.add_error(error_msg)
            return error_msg, {"error": error_msg}

        # Parse and execute actions
        self.log(f"[PROCESS] Parsing agent response...")
        actions = self.parse_agent_response(agent_response)

        self.log(f"[PROCESS] Executing {len(actions)} actions...")
        results = self.execute_actions(actions)

        # Check if data was collected and needs analysis
        if results.get("data_collected") and not results.get("completed"):
            self.log(f"[PROCESS] Data collected, prompting for analysis...")

            # Build status message about collected data
            data_status = self._build_data_status_message()

            # Inject a system message about available data
            follow_up_prompt = f"""The sub-agents have completed data collection. Here's what's available:

{data_status}

Please analyze the collected data and provide results to the user. Use the <analysis> command if you need to process the data, then use <user_message> to present your findings."""

            self.context.conversation_history.append({"role": "user", "content": follow_up_prompt})

            # Call LLM again for analysis
            try:
                self.log(f"[PROCESS-FOLLOWUP] Requesting analysis of collected data")
                follow_up_response = self.anthropic_client.messages.create(
                    model="claude-sonnet-4-20250514",
                    max_tokens=4096,
                    system=MAIN_AGENT_SYSTEM_PROMPT,
                    messages=self.context.conversation_history,
                    temperature=0.1
                )

                follow_up_text = follow_up_response.content[0].text
                self.log(f"[PROCESS-FOLLOWUP] Got analysis response of length {len(follow_up_text)}")

                # Parse and execute follow-up actions
                follow_up_actions = self.parse_agent_response(follow_up_text)
                follow_up_results = self.execute_actions(follow_up_actions)

                # Merge results
                results["messages"].extend(follow_up_results.get("messages", []))
                results["errors"].extend(follow_up_results.get("errors", []))
                if follow_up_results.get("completed"):
                    results["completed"] = True

                # Add follow-up to conversation history
                self.context.conversation_history.append({"role": "assistant", "content": follow_up_text})
                agent_response += "\n\n" + follow_up_text

            except Exception as e:
                error_msg = f"Follow-up analysis failed: {str(e)}"
                self.log(f"[PROCESS-FOLLOWUP-ERROR] {error_msg}")
                results["errors"].append(error_msg)

        # Create summary
        self.log(f"[PROCESS] Creating summary...")
        summary = self.context.get_summary()
        summary["results"] = results

        self.log(f"[PROCESS] Request processing complete")
        return agent_response, summary

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
                response, summary = self.process_request(user_input)
                print(f"\nAssistant: {response}")

                # Show any errors
                if summary.get("results", {}).get("errors"):
                    print(f"\n⚠️ Errors occurred:")
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

    def _build_data_status_message(self) -> str:
        """Build a status message about collected data"""
        status_parts = []

        # Check each stored DataFrame
        for key, df in self.context.dataframes.items():
            if isinstance(df, pl.DataFrame):
                if df.is_empty():
                    status_parts.append(f"- {key}: Empty DataFrame (0 rows)")
                else:
                    cols_preview = ", ".join(df.columns[:5])
                    if len(df.columns) > 5:
                        cols_preview += f" ... ({len(df.columns)} total columns)"
                    status_parts.append(f"- {key}: DataFrame with {len(df)} rows, columns: [{cols_preview}]")

        # Check for errors
        if self.context.errors:
            status_parts.append(f"\nErrors encountered: {len(self.context.errors)}")
            for error in self.context.errors[-3:]:  # Show last 3 errors
                status_parts.append(f"  - {error}")

        # Check task status
        task_summary = self.context.get_summary()
        status_parts.append(f"\nTask Summary: {task_summary['completed']} completed, {task_summary['failed']} failed")

        return "\n".join(status_parts)

    def save_results(self):
        """Save all collected data to files"""
        output_dir = f"output/session_{self.session_id}"
        os.makedirs(output_dir, exist_ok=True)

        # Save dataframes
        for key, df in self.context.dataframes.items():
            if isinstance(df, pl.DataFrame) and not df.is_empty():
                file_path = f"{output_dir}/{key}.parquet"
                df.write_parquet(file_path)
                self.log(f"Saved {key} to {file_path}")

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