"""
ResearchAgent - Main agentic loop for Agent V5
"""
import os
from typing import List, Dict, AsyncGenerator
from anthropic import Anthropic
from agent_v5.tools.registry import ToolRegistry
from debug import log, with_session
from agent_v5.tools.bash import BashTool
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
        self._register_core_tools()
        self.anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.run = with_session(session_id)(self.run)

    def _register_core_tools(self):
        """Register all core tools"""
        self.tools.register(BashTool(self.workspace_dir))
        self.tools.register(ReadTool(self.workspace_dir))
        self.tools.register(WriteTool(self.workspace_dir))
        self.tools.register(EditTool(self.workspace_dir))
        self.tools.register(GlobTool(self.workspace_dir))
        self.tools.register(GrepTool(self.workspace_dir))
        self.tools.register(TodoWriteTool(self.workspace_dir))
        self.tools.register(CohortDefinitionTool(self.workspace_dir))

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

            self.conversation_history.append({
                "role": "user",
                "content": tool_results
            })

        yield {"type": "done"}
