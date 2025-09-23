import os
import sys
import re
import time
import pandas as pd
from typing import List, Dict, Union
from dotenv import load_dotenv
from openai import OpenAI
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.main_prompt import MAIN_AGENT_SYSTEM_PROMPT, ANALYSIS_PROMPT
from agent.rx_claims_agent import RXClaimsAgent
from agent.med_claims_agent import MedClaimsAgent

load_dotenv()

class MainAgent:
    def __init__(self):
        self.openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.rx_claims_agent = RXClaimsAgent()
        self.med_claims_agent = MedClaimsAgent()
        self.conversation_history: List[Dict[str, str]] = []
        self.session_start_time = time.strftime("%Y%m%d_%H%M%S")
        self.trace_log: List[str] = []
        self.stored_results: Dict[str, Union[pd.DataFrame, str]] = {}
        self.workflow_complete = False
        
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
            if isinstance(data, pd.DataFrame):
                columns = list(data.columns)
                rows = len(data)
                available_dfs.append(f"{key}: DataFrame with {rows} rows, columns: {columns}")
            else:
                available_dfs.append(f"{key}: Error data (string)")
        
        df_info = "\n".join(available_dfs)
        
        messages = [
            {"role": "system", "content": ANALYSIS_PROMPT},
            {"role": "user", "content": f"Available DataFrames with actual schemas:\n{df_info}\n\nAnalysis Request: {analysis_request}"}
        ]
        
        response = self.openai_client.chat.completions.create(
            model="gpt-4o",
            messages=messages,
            temperature=0.1
        )
        
        analysis_response = response.choices[0].message.content
        
        code_match = re.search(r'```python\n(.*?)\n```', analysis_response, re.DOTALL)
        if code_match:
            pandas_code = code_match.group(1)
            
            local_vars = {'pd': pd}
            for key, df in self.stored_results.items():
                if isinstance(df, pd.DataFrame):
                    local_vars[key] = df
            
            try:
                exec(pandas_code, {"__builtins__": __builtins__, "pd": pd}, local_vars)
                
                if 'result' in local_vars:
                    result_df = local_vars['result']
                    if isinstance(result_df, pd.DataFrame):
                        self.stored_results['final_result'] = result_df
                        if len(result_df) > 10:
                            sample = result_df.head(10).to_string(index=False)
                            return f"Analysis completed. Result DataFrame with {len(result_df)} rows (showing first 10):\n{sample}\n\n... and {len(result_df)-10} more rows"
                        else:
                            return f"Analysis completed. Result DataFrame with {len(result_df)} rows:\n{result_df.to_string(index=False)}"
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

        return commands
    
    def execute_commands(self, commands: List[Dict[str, str]]) -> tuple[str, List[str]]:
        execution_log = []
        status_updates = []
        
        for command in commands:
            cmd_type = command["type"]
            cmd_content = command["content"]
            timestamp = time.strftime("%H:%M:%S")
            
            if cmd_type == "think":
                log_entry = f"[THINKING]: {cmd_content}"
                execution_log.append(log_entry)
                self.trace_log.append(f"[{timestamp}] {log_entry}")
                
            elif cmd_type == "user_message":
                log_entry = f"[USER MESSAGE]: {cmd_content}"
                execution_log.append(log_entry)
                self.trace_log.append(f"[{timestamp}] {log_entry}")
                status_updates.append("WAITING_FOR_USER_INPUT")
                
            elif cmd_type == "output":
                log_entry = f"[FINAL OUTPUT]: {cmd_content}"
                execution_log.append(log_entry)
                self.trace_log.append(f"[{timestamp}] {log_entry}")
                status_updates.append("WORKFLOW_COMPLETE")
                try:
                    ts = time.strftime("%Y%m%d_%H%M%S")
                    for key, df in self.stored_results.items():
                        if isinstance(df, pd.DataFrame) and not df.empty:
                            out_path = f"output/{key}_{ts}.csv"
                            df.to_csv(out_path, index=False)
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
                try:
                    result = self.rx_claims_agent.get_data(cmd_content, save_output=True)
                    result_key = f"rx_claims_{len(self.stored_results)}"
                    self.stored_results[result_key] = result
                    
                    if isinstance(result, pd.DataFrame):
                        if result.empty:
                            status_updates.append(f"RX Claims query successful: No results found (stored as {result_key})")
                            result_summary = "No results found"
                        else:
                            status_updates.append(f"RX Claims query successful: Found {len(result)} rows (stored as {result_key})")
                            result_summary = f"DataFrame with {len(result)} rows, columns: {list(result.columns)}"
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
                try:
                    result = self.med_claims_agent.get_data(cmd_content, save_output=True)
                    result_key = f"med_claims_{len(self.stored_results)}"
                    self.stored_results[result_key] = result
                    
                    if isinstance(result, pd.DataFrame):
                        if result.empty:
                            status_updates.append(f"Med Claims query successful: No results found (stored as {result_key})")
                            result_summary = "No results found"
                        else:
                            status_updates.append(f"Med Claims query successful: Found {len(result)} rows (stored as {result_key})")
                            result_summary = f"DataFrame with {len(result)} rows, columns: {list(result.columns)}"
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
        messages = [{"role": "system", "content": MAIN_AGENT_SYSTEM_PROMPT}]
        
        for msg in self.conversation_history:
            messages.append(msg)
        
        if user_input:
            messages.append({"role": "user", "content": user_input})
        
        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-4o",
                messages=messages,
            )
            
            agent_response = response.choices[0].message.content
            return agent_response
            
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def process_turn(self, user_input: str = None) -> str:
        if user_input:
            self.add_to_history("user", user_input)
        
        agent_response = self.generate_response()
        
        commands = self.parse_commands(agent_response)
        execution_log, status_updates = self.execute_commands(commands)
        
        self.add_to_history("assistant", agent_response)
        
        status_section = ""
        if status_updates:
            status_summary = "\n".join(status_updates)
            available_data = f"Available stored data: {list(self.stored_results.keys())}" if self.stored_results else "No stored data available"
            self.add_to_history("system", f"EXECUTION STATUS:\n{status_summary}\n{available_data}")
            status_section = f"\n\n=== STATUS ===\n{status_summary}"
        
        return f"=== AGENT RESPONSE ===\n{agent_response}\n\n=== EXECUTION LOG ===\n{execution_log}{status_section}"
    
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
                    
                    workflow_complete = False
                    waiting_for_user = False
                    
                    while not workflow_complete and not waiting_for_user:
                        try:
                            response = self.process_turn()
                            print(f"\n{response}")
                            
                            if self.workflow_complete or "WORKFLOW_COMPLETE" in response:
                                workflow_complete = True
                            elif "WAITING_FOR_USER_INPUT" in response:
                                waiting_for_user = True
                                
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
