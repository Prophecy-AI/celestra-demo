"""
ResearchAgent - Main agentic loop for Agent V5
"""
import os
import asyncio
import time
from typing import List, Dict, AsyncGenerator
from anthropic import Anthropic
from agent_v5.tools.registry import ToolRegistry
from debug import log, with_session
from agent_v5.tools.bash import BashTool
from agent_v5.tools.bash_output import ReadBashOutputTool
from agent_v5.tools.kill_shell import KillShellTool
from agent_v5.tools.bash_process_registry import BashProcessRegistry
from agent_v5.tools.read import ReadTool
from agent_v5.tools.write import WriteTool
from agent_v5.tools.edit import EditTool
from agent_v5.tools.glob import GlobTool
from agent_v5.tools.grep import GrepTool
from agent_v5.tools.todo import TodoWriteTool
from agent_v5.tools.cohort import CohortDefinitionTool


class ResearchAgent:
    """Research agent with agentic loop"""

    def __init__(self, session_id: str, workspace_dir: str, system_prompt: str):
        self.session_id = session_id
        self.workspace_dir = workspace_dir
        self.system_prompt = system_prompt
        self.conversation_history: List[Dict] = []
        self.tools = ToolRegistry(workspace_dir)
        self.process_registry = BashProcessRegistry()  # Registry for background bash processes
        self._register_core_tools()
        self.anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.run = with_session(session_id)(self.run)

    def _register_core_tools(self):
        """Register all core tools"""
        self.tools.register(BashTool(self.workspace_dir, self.process_registry))
        self.tools.register(ReadBashOutputTool(self.workspace_dir, self.process_registry))
        self.tools.register(KillShellTool(self.workspace_dir, self.process_registry))
        self.tools.register(ReadTool(self.workspace_dir))
        self.tools.register(WriteTool(self.workspace_dir))
        self.tools.register(EditTool(self.workspace_dir))
        self.tools.register(GlobTool(self.workspace_dir))
        self.tools.register(GrepTool(self.workspace_dir))
        self.tools.register(TodoWriteTool(self.workspace_dir))
        self.tools.register(CohortDefinitionTool(self.workspace_dir))

    async def cleanup(self) -> None:
        """
        Cleanup agent resources (kills all background processes)

        IMPORTANT: Call this after agent.run() completes to prevent process leaks.
        Especially critical for long-running agents or when agent is cancelled.
        """
        killed = await self.process_registry.cleanup()
        if killed > 0:
            log(f"✓ Cleaned up {killed} background processes", 1)

    def _should_wait_for_process(self, tool_uses: List[Dict], tool_results: List[Dict]) -> bool:
        if len(tool_uses) != 1 or tool_uses[0]["name"] != "ReadBashOutput":
            return False
        content = tool_results[0]["content"]
        return "[RUNNING]" in content and "(no new output since last read)" in content

    async def _wait_for_process(self, shell_id: str) -> str:
        bg_process = self.process_registry.get(shell_id)
        if not bg_process:
            return "Process not found"
        
        while bg_process.process.returncode is None:
            await asyncio.sleep(30)
            log(f"→ Still waiting for {shell_id} (runtime: {time.time() - bg_process.start_time:.0f}s)")
        
        new_output = bg_process.stdout_data[bg_process.stdout_cursor:].decode('utf-8', errors='replace')
        new_output += bg_process.stderr_data[bg_process.stderr_cursor:].decode('utf-8', errors='replace')
        bg_process.stdout_cursor = len(bg_process.stdout_data)
        bg_process.stderr_cursor = len(bg_process.stderr_data)
        
        runtime = time.time() - bg_process.start_time
        exit_code = bg_process.process.returncode
        
        log(f"✓ {shell_id} completed (exit code: {exit_code}, runtime: {runtime:.0f}s)", 1)
        
        return (
            f"[COMPLETED] {shell_id} (exit code: {exit_code}, runtime: {runtime:.0f}s)\n"
            f"Command: {bg_process.command}\n\n"
            f"{new_output}"
        )

    async def run(self, user_message: str) -> AsyncGenerator[Dict, None]:
        """Main agentic loop"""
        log(f"→ Agent.run(session={self.session_id})")

        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        while True:
            response_content = []
            tool_uses = []

            log(f"→ API call (turn {len(self.conversation_history)//2})")

            with self.anthropic_client.messages.stream(
                model="claude-sonnet-4-5-20250929",
                max_tokens=20000,
                system=self.system_prompt,
                messages=self.conversation_history,
                tools=self.tools.get_schemas(),
                temperature=0,
            ) as stream:
                for event in stream:
                    if event.type == "content_block_start":
                        if event.content_block.type == "text":
                            yield {"type": "text_start"}

                    elif event.type == "content_block_delta":
                        if event.delta.type == "text_delta":
                            text = event.delta.text
                            response_content.append({"type": "text", "text": text})
                            yield {"type": "text_delta", "text": text}

                final_message = stream.get_final_message()
                for block in final_message.content:
                    if block.type == "tool_use":
                        tool_uses.append({
                            "type": "tool_use",
                            "id": block.id,
                            "name": block.name,
                            "input": block.input
                        })

            self.conversation_history.append({
                "role": "assistant",
                "content": response_content + tool_uses
            })

            if not tool_uses:
                log("✓ Agent.run complete", 1)
                break

            log(f"→ Executing {len(tool_uses)} tools")

            tool_results = []
            for tool_use in tool_uses:
                result = await self.tools.execute(tool_use["name"], tool_use["input"])
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use["id"],
                    "content": result["content"],
                    "is_error": result.get("is_error", False)
                })

                yield {
                    "type": "tool_execution",
                    "tool_name": tool_use["name"],
                    "tool_input": tool_use["input"],
                    "tool_output": result["content"]
                }

            if self._should_wait_for_process(tool_uses, tool_results):
                shell_id = tool_uses[0]["input"]["shell_id"]
                log(f"→ Detected waiting, sleeping until {shell_id} completes")
                completion_result = await self._wait_for_process(shell_id)
                tool_results[0]["content"] = completion_result

            self.conversation_history.append({
                "role": "user",
                "content": tool_results
            })

        yield {"type": "done"}
