import os
import sys
import re
import time
import polars as pl
from typing import List, Dict, Union
from dotenv import load_dotenv
# from openai import OpenAI
import anthropic

# Global debug flag
DEBUG = os.getenv('DEBUG', '0') == '1'

def debug_log(message: str, agent: str = "MAIN"):
    """Centralized debug logging with timestamps"""
    if DEBUG:
        timestamp = time.strftime("%H:%M:%S.%f")[:-3]  # Include milliseconds
        print(f"[{timestamp}] [{agent}] {message}")

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.main_prompt import MAIN_AGENT_SYSTEM_PROMPT, ANALYSIS_PROMPT
from agent.rx_claims_agent import RXClaimsAgent
from agent.med_claims_agent import MedClaimsAgent

load_dotenv()

class MainAgent:
    def __init__(self):
        debug_log("Initializing MainAgent")
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.rx_claims_agent = RXClaimsAgent()
        self.med_claims_agent = MedClaimsAgent()
        self.conversation_history: List[Dict[str, str]] = []
        self.session_start_time = time.strftime("%Y%m%d_%H%M%S")
        self.trace_log: List[str] = []
        self.stored_results: Dict[str, Union[pl.DataFrame, str]] = {}
        self.workflow_complete = False
        debug_log("MainAgent initialized")
        
    def add_to_history(self, role: str, content: str):
        self.conversation_history.append({"role": role, "content": content})
        timestamp = time.strftime("%H:%M:%S")
        self.trace_log.append(f"[{timestamp}] {role.upper()}: {content}")
    
    def save_trace_log(self):
        filename = f"output/main_agent_trace_{self.session_start_time}.txt"
        with open(filename, 'w') as f:
            f.write(f"Main Agent Conversation Trace\n")
            f.write(f"Session Started: {self.session_start_time}\n")
            f.write("=" * 80 + "\n\n")
            
            for entry in self.trace_log:
                f.write(entry + "\n\n")
            
            f.write("=" * 80 + "\n")
            f.write(f"Session Ended: {time.strftime('%Y%m%d_%H%M%S')}\n")
        
        return filename
    
    def execute_analysis(self, analysis_request: str) -> str:
        available_dfs = []
        for key, data in self.stored_results.items():
            if isinstance(data, pl.DataFrame):
                columns = data.columns
                rows = len(data)
                available_dfs.append(f"{key}: DataFrame with {rows} rows, columns: {columns}")
            else:
                available_dfs.append(f"{key}: Error data (string)")
        
        df_info = "\n".join(available_dfs)
        
        messages = [
            {"role": "user", "content": f"Available DataFrames with actual schemas:\n{df_info}\n\nAnalysis Request: {analysis_request}"}
        ]

        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            system=ANALYSIS_PROMPT,
            messages=messages,
            temperature=0.1
        )

        if hasattr(response, 'content') and len(response.content) > 0:
            analysis_response = response.content[0].text
        else:
            return f"Error: Unexpected analysis response structure: {response}"
        
        code_match = re.search(r'```python\n(.*?)\n```', analysis_response, re.DOTALL)
        if code_match:
            pandas_code = code_match.group(1)
            
            local_vars = {'pl': pl}
            for key, df in self.stored_results.items():
                if isinstance(df, pl.DataFrame):
                    local_vars[key] = df

            try:
                exec(pandas_code, {"__builtins__": __builtins__, "pl": pl}, local_vars)
                
                if 'result' in local_vars:
                    result_df = local_vars['result']
                    if isinstance(result_df, pl.DataFrame):
                        self.stored_results['final_result'] = result_df
                        if len(result_df) > 10:
                            sample = str(result_df.head(10))
                            return f"Analysis completed. Result DataFrame with {len(result_df)} rows (showing first 10):\n{sample}\n\n... and {len(result_df)-10} more rows"
                        else:
                            return f"Analysis completed. Result DataFrame with {len(result_df)} rows:\n{str(result_df)}"
                    else:
                        return f"Analysis completed. Result: {result_df}"
                else:
                    return "Analysis code executed but no 'result' variable found"
                    
            except Exception as e:
                return f"Error executing pandas code: {str(e)}\n\nGenerated code:\n{pandas_code}"
        else:
            return f"No pandas code found in analysis response:\n{analysis_response}"
        
    def parse_commands(self, response: str) -> List[Dict[str, str]]:
        commands = []
        
        think_match = re.search(r'<think>(.*?)</think>', response, re.DOTALL)
        if think_match:
            commands.append({"type": "think", "content": think_match.group(1).strip()})
        
        user_msg_match = re.search(r'<user_message>(.*?)</user_message>', response, re.DOTALL)
        if user_msg_match:
            commands.append({"type": "user_message", "content": user_msg_match.group(1).strip()})
        
        output_match = re.search(r'<output>(.*?)</output>', response, re.DOTALL)
        if output_match:
            commands.append({"type": "output", "content": output_match.group(1).strip()})
        
        rx_match = re.search(r'<rx_claims_agent>(.*?)</rx_claims_agent>', response, re.DOTALL)
        if rx_match:
            commands.append({"type": "rx_claims_agent", "content": rx_match.group(1).strip()})
        
        med_match = re.search(r'<med_claims_agent>(.*?)</med_claims_agent>', response, re.DOTALL)
        if med_match:
            commands.append({"type": "med_claims_agent", "content": med_match.group(1).strip()})
        
        analysis_match = re.search(r'<analysis>(.*?)</analysis>', response, re.DOTALL)
        if analysis_match:
            commands.append({"type": "analysis", "content": analysis_match.group(1).strip()})

        debug_log(f"Parsed {len(commands)} commands: {[cmd['type'] for cmd in commands]}")
        return commands
    
    def execute_commands(self, commands: List[Dict[str, str]]) -> tuple[str, List[str]]:
        debug_log(f"Executing {len(commands)} commands")
        execution_log = []
        status_updates = []
        
        for command in commands:
            cmd_type = command["type"]
            cmd_content = command["content"]
            timestamp = time.strftime("%H:%M:%S")
            debug_log(f"Executing command: {cmd_type}")

            
            if cmd_type == "think":
                debug_log(f"Thinking: {cmd_content[:100]}...", "MAIN")
                log_entry = f"[THINKING]: {cmd_content}"
                execution_log.append(log_entry)
                self.trace_log.append(f"[{timestamp}] {log_entry}")
                
            elif cmd_type == "user_message":
                debug_log(f"Sending user message: {cmd_content[:100]}...", "MAIN")
                log_entry = f"[USER MESSAGE]: {cmd_content}"
                execution_log.append(log_entry)
                self.trace_log.append(f"[{timestamp}] {log_entry}")
                status_updates.append("WAITING_FOR_USER_INPUT")
                
            elif cmd_type == "output":
                debug_log(f"Final output: {cmd_content[:100]}...", "MAIN")
                log_entry = f"[FINAL OUTPUT]: {cmd_content}"
                execution_log.append(log_entry)
                self.trace_log.append(f"[{timestamp}] {log_entry}")
                status_updates.append("WORKFLOW_COMPLETE")
                try:
                    ts = time.strftime("%Y%m%d_%H%M%S")
                    for key, df in self.stored_results.items():
                        if isinstance(df, pl.DataFrame) and not df.is_empty():
                            out_path = f"output/{key}_{ts}.csv"
                            df.write_csv(out_path)
                            save_log = f"[DATA SAVED]: {out_path}"
                            execution_log.append(save_log)
                            self.trace_log.append(f"[{timestamp}] {save_log}")
                except Exception as e:
                    err_log = f"[FINAL RESULT SAVE ERROR]: {str(e)}"
                    execution_log.append(err_log)
                    self.trace_log.append(f"[{timestamp}] {err_log}")
                self.workflow_complete = True
                
            elif cmd_type == "rx_claims_agent":
                call_log = f"[CALLING RX CLAIMS AGENT]: {cmd_content}"
                execution_log.append(call_log)
                self.trace_log.append(f"[{timestamp}] {call_log}")
                debug_log(f"Calling RX Claims Agent: {cmd_content}")
                try:
                    result = self.rx_claims_agent.get_data(cmd_content, save_output=True)
                    debug_log(f"RX Claims Agent returned: {type(result)}")
                    result_key = f"rx_claims_{len(self.stored_results)}"
                    self.stored_results[result_key] = result
                    
                    if isinstance(result, pl.DataFrame):
                        if result.is_empty():
                            status_updates.append(f"RX Claims query successful: No results found (stored as {result_key})")
                            result_summary = "No results found"
                        else:
                            status_updates.append(f"RX Claims query successful: Found {len(result)} rows (stored as {result_key})")
                            result_summary = f"DataFrame with {len(result)} rows, columns: {result.columns}"
                    else:
                        status_updates.append(f"RX Claims query completed (stored as {result_key})")
                        result_summary = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                    
                    result_log = f"[RX CLAIMS RESULT]: {result_summary}"
                    execution_log.append(result_log)
                    self.trace_log.append(f"[{timestamp}] {result_log}")
                except Exception as e:
                    error_log = f"[RX CLAIMS ERROR]: {str(e)}"
                    execution_log.append(error_log)
                    self.trace_log.append(f"[{timestamp}] {error_log}")
                    status_updates.append(f"RX Claims query failed: {str(e)}")
                    
            elif cmd_type == "med_claims_agent":
                call_log = f"[CALLING MED CLAIMS AGENT]: {cmd_content}"
                execution_log.append(call_log)
                self.trace_log.append(f"[{timestamp}] {call_log}")
                debug_log(f"Calling Med Claims Agent: {cmd_content}")
                try:
                    result = self.med_claims_agent.get_data(cmd_content, save_output=True)
                    debug_log(f"Med Claims Agent returned: {type(result)}")
                    result_key = f"med_claims_{len(self.stored_results)}"
                    self.stored_results[result_key] = result
                    
                    if isinstance(result, pl.DataFrame):
                        if result.is_empty():
                            status_updates.append(f"Med Claims query successful: No results found (stored as {result_key})")
                            result_summary = "No results found"
                        else:
                            status_updates.append(f"Med Claims query successful: Found {len(result)} rows (stored as {result_key})")
                            result_summary = f"DataFrame with {len(result)} rows, columns: {result.columns}"
                    else:
                        status_updates.append(f"Med Claims query completed (stored as {result_key})")
                        result_summary = str(result)[:200] + "..." if len(str(result)) > 200 else str(result)
                    
                    result_log = f"[MED CLAIMS RESULT]: {result_summary}"
                    execution_log.append(result_log)
                    self.trace_log.append(f"[{timestamp}] {result_log}")
                except Exception as e:
                    error_log = f"[MED CLAIMS ERROR]: {str(e)}"
                    execution_log.append(error_log)
                    self.trace_log.append(f"[{timestamp}] {error_log}")
                    status_updates.append(f"Med Claims query failed: {str(e)}")
                    
            elif cmd_type == "analysis":
                debug_log(f"Analysis request: {cmd_content[:100]}...", "MAIN")
                log_entry = f"[ANALYSIS REQUEST]: {cmd_content}"
                execution_log.append(log_entry)
                self.trace_log.append(f"[{timestamp}] {log_entry}")
                
                try:
                    analysis_result = self.execute_analysis(cmd_content)
                    result_log = f"[ANALYSIS RESULT]: {analysis_result}"
                    execution_log.append(result_log)
                    self.trace_log.append(f"[{timestamp}] {result_log}")
                    status_updates.append("Analysis completed successfully")
                except Exception as e:
                    error_log = f"[ANALYSIS ERROR]: {str(e)}"
                    execution_log.append(error_log)
                    self.trace_log.append(f"[{timestamp}] {error_log}")
                    status_updates.append(f"Analysis failed: {str(e)}")
                
            elif cmd_type == "get_stored_data":
                data_key = cmd_content.strip()
                if data_key in self.stored_results:
                    retrieved_data = self.stored_results[data_key]
                    log_entry = f"[RETRIEVED DATA {data_key}]: {retrieved_data}"
                    execution_log.append(log_entry)
                    self.trace_log.append(f"[{timestamp}] {log_entry}")
                    status_updates.append(f"Successfully retrieved stored data: {data_key}")
                else:
                    error_log = f"[DATA ERROR]: Key '{data_key}' not found in stored results. Available keys: {list(self.stored_results.keys())}"
                    execution_log.append(error_log)
                    self.trace_log.append(f"[{timestamp}] {error_log}")
                    status_updates.append(f"Failed to retrieve data: Key '{data_key}' not found")
        
        return "\n\n".join(execution_log), status_updates
    
    def generate_response(self, user_input: str = None) -> str:
        messages = []

        for msg in self.conversation_history:
            if msg["role"] != "system":  # Skip system messages from history
                messages.append(msg)

        if user_input:
            messages.append({"role": "user", "content": user_input})

        # Don't call API if no new content to process
        if not user_input and not messages:
            debug_log("No new input or conversation context, skipping API call")
            return "No new input to process."

        try:
            response = self.anthropic_client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=4096,
                system=MAIN_AGENT_SYSTEM_PROMPT,
                messages=messages
            )

            debug_log(f"Anthropic API Response: {len(response.content)} content blocks, {getattr(response.usage, 'output_tokens', 0)} tokens")

            if hasattr(response, 'content') and len(response.content) > 0:
                agent_response = response.content[0].text
                return agent_response
            else:
                return f"Error: Unexpected response structure: {response}"

        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def process_turn(self, user_input: str = None) -> str:
        if user_input:
            debug_log(f"Processing user input: {user_input}")
            self.add_to_history("user", user_input)
        else:
            debug_log("Processing turn with no new user input")

        agent_response = self.generate_response(user_input)

        commands = self.parse_commands(agent_response)
        execution_log, status_updates = self.execute_commands(commands)

        self.add_to_history("assistant", agent_response)

        # Handle status updates for internal tracking
        if status_updates:
            status_summary = "\n".join(status_updates)
            available_data = f"Available stored data: {list(self.stored_results.keys())}" if self.stored_results else "No stored data available"
            self.add_to_history("system", f"EXECUTION STATUS:\n{status_summary}\n{available_data}")

            # Log status updates to debug log
            for update in status_updates:
                debug_log(f"Status: {update}")

        # Always return clean agent response - debug info goes to debug_log()
        return agent_response
    
    def chat(self):
        print("Orchestrator Agent started. Type 'quit' to exit.")
        print("Agent will auto-continue until it asks a question or completes the workflow.")
        
        try:
            while True:
                try:
                    user_input = input("\nYou: ").strip()
                    
                    if user_input.lower() in ['quit', 'exit', 'q']:
                        break
                    
                    response = self.process_turn(user_input)
                    print(f"\n{response}")

                    if self.workflow_complete:
                        print("\n=== WORKFLOW COMPLETED ===")
                        break

                    # Initialize auto-continue state
                    workflow_complete = self.workflow_complete
                    waiting_for_user = False

                    # Check if we need to wait for user input after the initial response
                    if "<user_message>" in response:
                        debug_log("Agent requests user input, returning to input prompt")
                        waiting_for_user = True

                    # Check if we have fresh sub-agent results that need to be presented
                    if self.stored_results and not waiting_for_user:
                        # Get the most recent result key
                        recent_keys = [k for k in self.stored_results.keys() if k.startswith(('med_claims_', 'rx_claims_')) and isinstance(self.stored_results[k], pl.DataFrame)]
                        if recent_keys:
                            latest_key = max(recent_keys)
                            latest_df = self.stored_results[latest_key]
                            debug_log(f"Presenting results from {latest_key}")
                            if not latest_df.is_empty():
                                print(f"\nHere are the results from {latest_key}:")
                                print(latest_df)
                            else:
                                print(f"\nNo data found in {latest_key}")
                            waiting_for_user = True

                    # Auto-continue only if agent has actionable work to do
                    while not workflow_complete and not waiting_for_user:
                        try:
                            response = self.process_turn()
                            print(f"\n{response}")

                            # Check for completion or blocking conditions
                            if self.workflow_complete or "WORKFLOW_COMPLETE" in response:
                                workflow_complete = True
                                break
                            elif "WAITING_FOR_USER_INPUT" in response:
                                waiting_for_user = True
                                break
                            elif "No new input to process" in response:
                                debug_log("Agent has no new work, stopping auto-continue")
                                break
                            elif "Error: Unexpected response structure" in response:
                                debug_log("Empty API response detected, stopping auto-continue")
                                break
                            else:
                                # Check if any commands were parsed - if not, agent is done
                                commands = self.parse_commands(response)
                                if not commands:
                                    debug_log("No commands parsed, agent completed work, stopping auto-continue")
                                    break
                                
                        except Exception as e:
                            print(f"Error in auto-continue: {e}")
                            break
                    
                    if workflow_complete:
                        print("\n=== WORKFLOW COMPLETED ===")
                        break
                except KeyboardInterrupt:
                    break
                except Exception as e:
                    print(f"Error: {e}")
        
        finally:
            filename = self.save_trace_log()
            print(f"\nConversation trace saved to {filename}")
            print("Goodbye!")

def main():
    agent = MainAgent()
    agent.chat()

if __name__ == "__main__":
    main()
