⏺ Ultra-Detailed Implementation Plan: Agent V5 (Claude Code Independence)

  EXECUTIVE SUMMARY

  We're building a research engineer agent that operates in Modal sandboxes, maintains
   persistent workspaces, and executes BigQuery analyses—without the Claude Code SDK
  dependency. The agent will be prompted by non-technical users for research tasks.

  ---
  1. CONTROL FLOW LOOP

  Core Architecture

  class ResearchAgent:
      def __init__(self, session_id: str, workspace_dir: str, system_prompt: str):
          self.session_id = session_id
          self.workspace_dir = workspace_dir
          self.system_prompt = system_prompt
          self.conversation_history = []
          self.tools = self._initialize_tools()
          self.anthropic_client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

      async def run(self, user_message: str):
          """Main agentic loop"""
          # 1. Add user message to history
          self.conversation_history.append({
              "role": "user",
              "content": user_message
          })

          # 2. Loop until no more tool uses
          while True:
              # 3. Call Claude API with streaming
              response_content = []
              tool_uses = []

              async with self.anthropic_client.messages.stream(
                  model="claude-sonnet-4-5-20250929",
                  max_tokens=8192,
                  system=self._build_system_prompt(),
                  messages=self.conversation_history,
                  tools=self._get_tool_schemas(),
              ) as stream:
                  async for event in stream:
                      # 4. Parse streaming chunks
                      if event.type == "content_block_start":
                          if event.content_block.type == "text":
                              yield {"type": "text_start"}
                      elif event.type == "content_block_delta":
                          if event.delta.type == "text_delta":
                              text = event.delta.text
                              response_content.append({"type": "text", "text": text})
                              yield {"type": "text_delta", "text": text}
                      elif event.type == "content_block_stop":
                          block = stream.current_content_block
                          if hasattr(block, 'type') and block.type == "tool_use":
                              tool_uses.append({
                                  "type": "tool_use",
                                  "id": block.id,
                                  "name": block.name,
                                  "input": block.input
                              })

              # 5. Add assistant response to history
              self.conversation_history.append({
                  "role": "assistant",
                  "content": response_content + tool_uses
              })

              # 6. If no tool uses, we're done
              if not tool_uses:
                  break

              # 7. Execute tools and collect results
              tool_results = []
              for tool_use in tool_uses:
                  result = await self._execute_tool(tool_use)
                  tool_results.append({
                      "type": "tool_result",
                      "tool_use_id": tool_use["id"],
                      "content": result["content"],
                      "is_error": result.get("is_error", False)
                  })

                  # Yield tool execution to user
                  yield {
                      "type": "tool_execution",
                      "tool_name": tool_use["name"],
                      "tool_input": tool_use["input"],
                      "tool_output": result["content"]
                  }

              # 8. Add tool results to history
              self.conversation_history.append({
                  "role": "user",
                  "content": tool_results
              })

          # 9. Return final response
          yield {"type": "done"}

  Key Design Decisions

  1. Streaming First: All text output streams to terminal in real-time
  2. Stateful Conversation: Full message history maintained for context
  3. Tool Loop: Continues until Claude doesn't request more tools
  4. Async Throughout: Modal's async runtime + Anthropic's async SDK

  ---
  2. TOOL IMPLEMENTATIONS

  Tool Registry System

  class ToolRegistry:
      def __init__(self, workspace_dir: str):
          self.workspace_dir = workspace_dir
          self.tools = {}
          self._register_core_tools()

      def _register_core_tools(self):
          """Register all built-in tools"""
          self.register(BashTool(self.workspace_dir))
          self.register(ReadTool(self.workspace_dir))
          self.register(WriteTool(self.workspace_dir))
          self.register(EditTool(self.workspace_dir))
          self.register(GlobTool(self.workspace_dir))
          self.register(GrepTool(self.workspace_dir))
          # ... etc

      def register(self, tool):
          self.tools[tool.name] = tool

      def get_schemas(self):
          """Return Anthropic-compatible tool schemas"""
          return [tool.schema for tool in self.tools.values()]

      async def execute(self, tool_name: str, tool_input: dict):
          """Execute a tool by name"""
          if tool_name not in self.tools:
              return {
                  "content": f"Unknown tool: {tool_name}",
                  "is_error": True
              }
          return await self.tools[tool_name].execute(tool_input)

  Base Tool Class

  from abc import ABC, abstractmethod

  class BaseTool(ABC):
      def __init__(self, workspace_dir: str):
          self.workspace_dir = workspace_dir

      @property
      @abstractmethod
      def name(self) -> str:
          pass

      @property
      @abstractmethod
      def schema(self) -> dict:
          """Anthropic tool schema"""
          pass

      @abstractmethod
      async def execute(self, input: dict) -> dict:
          """Execute tool and return result"""
          pass

  ---
  3. DETAILED TOOL SPECIFICATIONS

  3.1 Bash Tool

  Purpose: Execute shell commands in workspace

  class BashTool(BaseTool):
      name = "Bash"

      schema = {
          "name": "Bash",
          "description": "Execute shell commands in the workspace directory",
          "input_schema": {
              "type": "object",
              "properties": {
                  "command": {
                      "type": "string",
                      "description": "Shell command to execute"
                  },
                  "description": {
                      "type": "string",
                      "description": "Human-readable description of what this command
  does"
                  },
                  "timeout": {
                      "type": "number",
                      "description": "Timeout in milliseconds (max 600000)",
                      "default": 120000
                  }
              },
              "required": ["command"]
          }
      }

      async def execute(self, input: dict) -> dict:
          command = input["command"]
          timeout = input.get("timeout", 120000) / 1000  # Convert to seconds

          try:
              # Change to workspace directory
              process = await asyncio.create_subprocess_shell(
                  f"cd {self.workspace_dir} && {command}",
                  stdout=asyncio.subprocess.PIPE,
                  stderr=asyncio.subprocess.PIPE,
              )

              # Wait with timeout
              stdout, stderr = await asyncio.wait_for(
                  process.communicate(),
                  timeout=timeout
              )

              output = stdout.decode() + stderr.decode()

              # Truncate if too long (30k chars like Claude Code)
              if len(output) > 30000:
                  output = output[:30000] + "\n... (output truncated)"

              # Check if CWD changed (for Shell cwd tracking)
              cwd_check = await asyncio.create_subprocess_shell(
                  "pwd",
                  stdout=asyncio.subprocess.PIPE,
                  cwd=self.workspace_dir
              )
              new_cwd, _ = await cwd_check.communicate()

              if new_cwd.decode().strip() != self.workspace_dir:
                  output += f"\nShell cwd was reset to {new_cwd.decode().strip()}"

              return {
                  "content": output,
                  "is_error": False
              }

          except asyncio.TimeoutError:
              return {
                  "content": f"Command timed out after {timeout}s",
                  "is_error": True
              }
          except Exception as e:
              return {
                  "content": f"Error executing command: {str(e)}",
                  "is_error": True
              }

  Implementation Notes:
  - Uses asyncio.create_subprocess_shell for async execution
  - Timeout enforcement (default 120s, max 600s)
  - Output truncation at 30k characters
  - CWD tracking (Claude Code does this)
  - Error handling for permissions, missing commands

  ---
  3.2 Read Tool

  Purpose: Read file contents with optional offset/limit

  class ReadTool(BaseTool):
      name = "Read"

      schema = {
          "name": "Read",
          "description": "Read file contents from workspace",
          "input_schema": {
              "type": "object",
              "properties": {
                  "file_path": {
                      "type": "string",
                      "description": "Absolute path to file"
                  },
                  "offset": {
                      "type": "number",
                      "description": "Line number to start reading from"
                  },
                  "limit": {
                      "type": "number",
                      "description": "Number of lines to read"
                  }
              },
              "required": ["file_path"]
          }
      }

      async def execute(self, input: dict) -> dict:
          file_path = input["file_path"]
          offset = input.get("offset", 0)
          limit = input.get("limit", 2000)  # Default 2000 lines

          try:
              # Resolve path (handle relative paths relative to workspace)
              if not file_path.startswith('/'):
                  file_path = os.path.join(self.workspace_dir, file_path)

              # Read file
              with open(file_path, 'r') as f:
                  lines = f.readlines()

              # Apply offset and limit
              selected_lines = lines[offset:offset + limit]

              # Format with line numbers (cat -n style)
              numbered_lines = []
              for i, line in enumerate(selected_lines, start=offset + 1):
                  # Truncate lines > 2000 chars
                  if len(line) > 2000:
                      line = line[:2000] + "... (line truncated)\n"
                  numbered_lines.append(f"{i:6d}→{line}")

              content = "".join(numbered_lines)

              # Check for empty file warning
              if not content.strip():
                  content = "<system-reminder>\nThis file exists but is
  empty.\n</system-reminder>"

              return {
                  "content": content,
                  "is_error": False
              }

          except FileNotFoundError:
              return {
                  "content": f"File not found: {file_path}",
                  "is_error": True
              }
          except Exception as e:
              return {
                  "content": f"Error reading file: {str(e)}",
                  "is_error": True
              }

  Implementation Notes:
  - Handles absolute and relative paths
  - Line numbering with cat -n format (6 chars + arrow)
  - Line truncation at 2000 characters
  - Default 2000 line limit
  - Empty file warning
  - Image/PDF reading would need special handling (for MVP: skip or use PIL/PyPDF2)

  ---
  3.3 Write Tool

  Purpose: Create or overwrite files

  class WriteTool(BaseTool):
      name = "Write"

      schema = {
          "name": "Write",
          "description": "Write content to a file (creates or overwrites)",
          "input_schema": {
              "type": "object",
              "properties": {
                  "file_path": {
                      "type": "string",
                      "description": "Absolute path to file"
                  },
                  "content": {
                      "type": "string",
                      "description": "Content to write"
                  }
              },
              "required": ["file_path", "content"]
          }
      }

      async def execute(self, input: dict) -> dict:
          file_path = input["file_path"]
          content = input["content"]

          try:
              # Resolve path
              if not file_path.startswith('/'):
                  file_path = os.path.join(self.workspace_dir, file_path)

              # Check if file exists (for Read requirement check)
              file_exists = os.path.exists(file_path)

              # For Claude Code compatibility: require Read before overwriting
              # (This is hard to enforce without state tracking - might skip for MVP)

              # Create parent directories if needed
              os.makedirs(os.path.dirname(file_path), exist_ok=True)

              # Write file
              with open(file_path, 'w') as f:
                  f.write(content)

              if file_exists:
                  message = f"File updated successfully at: {file_path}"
              else:
                  message = f"File created successfully at: {file_path}"

              return {
                  "content": message,
                  "is_error": False
              }

          except Exception as e:
              return {
                  "content": f"Error writing file: {str(e)}",
                  "is_error": True
              }

  Implementation Notes:
  - Creates parent directories automatically
  - Distinguishes between create and overwrite in response
  - For full Claude Code parity: would need to track Read history (skip for MVP)

  ---
  3.4 Edit Tool

  Purpose: Exact string replacement in files

  class EditTool(BaseTool):
      name = "Edit"

      schema = {
          "name": "Edit",
          "description": "Replace exact string in file",
          "input_schema": {
              "type": "object",
              "properties": {
                  "file_path": {
                      "type": "string",
                      "description": "Absolute path to file"
                  },
                  "old_string": {
                      "type": "string",
                      "description": "Exact string to find"
                  },
                  "new_string": {
                      "type": "string",
                      "description": "String to replace with"
                  },
                  "replace_all": {
                      "type": "boolean",
                      "description": "Replace all occurrences (default false)",
                      "default": False
                  }
              },
              "required": ["file_path", "old_string", "new_string"]
          }
      }

      async def execute(self, input: dict) -> dict:
          file_path = input["file_path"]
          old_string = input["old_string"]
          new_string = input["new_string"]
          replace_all = input.get("replace_all", False)

          try:
              # Resolve path
              if not file_path.startswith('/'):
                  file_path = os.path.join(self.workspace_dir, file_path)

              # Read file
              with open(file_path, 'r') as f:
                  content = f.read()

              # Check if old_string exists
              if old_string not in content:
                  return {
                      "content": f"String not found in file: {old_string}",
                      "is_error": True
                  }

              # Check uniqueness unless replace_all
              if not replace_all and content.count(old_string) > 1:
                  return {
                      "content": f"String appears {content.count(old_string)} times.
  Use replace_all=true or provide more context.",
                      "is_error": True
                  }

              # Perform replacement
              if replace_all:
                  new_content = content.replace(old_string, new_string)
              else:
                  new_content = content.replace(old_string, new_string, 1)

              # Write back
              with open(file_path, 'w') as f:
                  f.write(new_content)

              # Show snippet of edit (like Claude Code does)
              # Find the changed section and show context
              lines = new_content.split('\n')
              # Find line containing new_string
              for i, line in enumerate(lines):
                  if new_string in line:
                      start = max(0, i - 2)
                      end = min(len(lines), i + 3)
                      snippet_lines = lines[start:end]
                      snippet = "\n".join([f"{j+start+1:6d}→{l}" for j, l in
  enumerate(snippet_lines)])
                      break
              else:
                  snippet = "(edit applied, no preview available)"

              return {
                  "content": f"The file {file_path} has been updated. Here's the
  result:\n{snippet}",
                  "is_error": False
              }

          except FileNotFoundError:
              return {
                  "content": f"File not found: {file_path}",
                  "is_error": True
              }
          except Exception as e:
              return {
                  "content": f"Error editing file: {str(e)}",
                  "is_error": True
              }

  Implementation Notes:
  - Exact string matching (must preserve indentation)
  - Uniqueness check (fails if multiple matches unless replace_all)
  - Shows snippet of edited region
  - Requires prior Read for Claude Code parity (can track in state)

  ---
  3.5 Glob Tool

  Purpose: Find files matching glob patterns

  import glob as glob_module

  class GlobTool(BaseTool):
      name = "Glob"

      schema = {
          "name": "Glob",
          "description": "Find files matching glob pattern",
          "input_schema": {
              "type": "object",
              "properties": {
                  "pattern": {
                      "type": "string",
                      "description": "Glob pattern (e.g., '**/*.py')"
                  },
                  "path": {
                      "type": "string",
                      "description": "Directory to search in (default: workspace)"
                  }
              },
              "required": ["pattern"]
          }
      }

      async def execute(self, input: dict) -> dict:
          pattern = input["pattern"]
          search_path = input.get("path", self.workspace_dir)

          try:
              # Resolve search path
              if not search_path.startswith('/'):
                  search_path = os.path.join(self.workspace_dir, search_path)

              # Build full pattern
              full_pattern = os.path.join(search_path, pattern)

              # Execute glob
              matches = glob_module.glob(full_pattern, recursive=True)

              # Sort by modification time (most recent first)
              matches.sort(key=lambda x: os.path.getmtime(x), reverse=True)

              if not matches:
                  return {
                      "content": "No files found",
                      "is_error": None  # Not an error, just no results
                  }

              # Return newline-separated paths
              return {
                  "content": "\n".join(matches),
                  "is_error": False
              }

          except Exception as e:
              return {
                  "content": f"Error globbing: {str(e)}",
                  "is_error": True
              }

  Implementation Notes:
  - Uses Python's built-in glob module
  - Supports ** for recursive matching
  - Sorts by modification time (Claude Code behavior)
  - Returns newline-separated paths

  ---
  3.6 Grep Tool

  Purpose: Search file contents with regex

  import re
  import subprocess

  class GrepTool(BaseTool):
      name = "Grep"

      schema = {
          "name": "Grep",
          "description": "Search file contents with regex (ripgrep-based)",
          "input_schema": {
              "type": "object",
              "properties": {
                  "pattern": {
                      "type": "string",
                      "description": "Regex pattern to search for"
                  },
                  "path": {
                      "type": "string",
                      "description": "File or directory to search (default:
  workspace)"
                  },
                  "glob": {
                      "type": "string",
                      "description": "Glob pattern to filter files (e.g., '*.py')"
                  },
                  "type": {
                      "type": "string",
                      "description": "File type filter (e.g., 'py', 'js')"
                  },
                  "-i": {
                      "type": "boolean",
                      "description": "Case insensitive search"
                  },
                  "-n": {
                      "type": "boolean",
                      "description": "Show line numbers"
                  },
                  "-A": {
                      "type": "number",
                      "description": "Lines of context after match"
                  },
                  "-B": {
                      "type": "number",
                      "description": "Lines of context before match"
                  },
                  "-C": {
                      "type": "number",
                      "description": "Lines of context around match"
                  },
                  "output_mode": {
                      "type": "string",
                      "enum": ["content", "files_with_matches", "count"],
                      "description": "Output mode (default: files_with_matches)"
                  },
                  "multiline": {
                      "type": "boolean",
                      "description": "Enable multiline mode"
                  },
                  "head_limit": {
                      "type": "number",
                      "description": "Limit output to first N results"
                  }
              },
              "required": ["pattern"]
          }
      }

      async def execute(self, input: dict) -> dict:
          pattern = input["pattern"]
          search_path = input.get("path", self.workspace_dir)
          output_mode = input.get("output_mode", "files_with_matches")

          try:
              # Build ripgrep command
              rg_args = ["rg"]

              # Pattern
              rg_args.append(pattern)

              # Case insensitive
              if input.get("-i"):
                  rg_args.append("-i")

              # Line numbers (only for content mode)
              if input.get("-n") and output_mode == "content":
                  rg_args.append("-n")

              # Context
              if input.get("-A") and output_mode == "content":
                  rg_args.extend(["-A", str(input["-A"])])
              if input.get("-B") and output_mode == "content":
                  rg_args.extend(["-B", str(input["-B"])])
              if input.get("-C") and output_mode == "content":
                  rg_args.extend(["-C", str(input["-C"])])

              # Glob filter
              if input.get("glob"):
                  rg_args.extend(["--glob", input["glob"]])

              # Type filter
              if input.get("type"):
                  rg_args.extend(["--type", input["type"]])

              # Multiline
              if input.get("multiline"):
                  rg_args.extend(["-U", "--multiline-dotall"])

              # Output mode
              if output_mode == "files_with_matches":
                  rg_args.append("-l")
              elif output_mode == "count":
                  rg_args.append("-c")
              # content mode is default (no flag needed)

              # Search path
              rg_args.append(search_path)

              # Execute ripgrep
              process = await asyncio.create_subprocess_exec(
                  *rg_args,
                  stdout=asyncio.subprocess.PIPE,
                  stderr=asyncio.subprocess.PIPE
              )
              stdout, stderr = await process.communicate()

              # Handle no matches (ripgrep exits with code 1)
              if process.returncode == 1:
                  return {
                      "content": "No matches found",
                      "is_error": None
                  }
              elif process.returncode != 0:
                  return {
                      "content": stderr.decode(),
                      "is_error": True
                  }

              output = stdout.decode()

              # Apply head limit
              if input.get("head_limit"):
                  lines = output.split('\n')
                  output = '\n'.join(lines[:input["head_limit"]])

              return {
                  "content": output,
                  "is_error": False
              }

          except FileNotFoundError:
              return {
                  "content": "ripgrep (rg) not found. Please install ripgrep.",
                  "is_error": True
              }
          except Exception as e:
              return {
                  "content": f"Error searching: {str(e)}",
                  "is_error": True
              }

  Implementation Notes:
  - Uses ripgrep (rg) for performance (must be installed in Modal image)
  - Supports all ripgrep features: case-insensitive, context lines, multiline, etc.
  - Three output modes: content (default), files_with_matches, count
  - Head limit for truncating results
  - Handles ripgrep exit codes (1 = no matches, not an error)

  ---
  3.7 TodoWrite Tool

  Purpose: Task list management

  class TodoWriteTool(BaseTool):
      name = "TodoWrite"

      def __init__(self, workspace_dir: str):
          super().__init__(workspace_dir)
          self.todos = []  # In-memory todo list

      schema = {
          "name": "TodoWrite",
          "description": "Create and update task list",
          "input_schema": {
              "type": "object",
              "properties": {
                  "todos": {
                      "type": "array",
                      "items": {
                          "type": "object",
                          "properties": {
                              "content": {
                                  "type": "string",
                                  "description": "Task description (imperative form)"
                              },
                              "activeForm": {
                                  "type": "string",
                                  "description": "Present continuous form (e.g.,
  'Running tests')"
                              },
                              "status": {
                                  "type": "string",
                                  "enum": ["pending", "in_progress", "completed"],
                                  "description": "Task status"
                              }
                          },
                          "required": ["content", "activeForm", "status"]
                      }
                  }
              },
              "required": ["todos"]
          }
      }

      async def execute(self, input: dict) -> dict:
          self.todos = input["todos"]

          # Validate: exactly one in_progress task
          in_progress_count = sum(1 for t in self.todos if t["status"] ==
  "in_progress")

          if in_progress_count > 1:
              return {
                  "content": "Warning: More than one task marked as in_progress. Only
  one task should be in_progress at a time.",
                  "is_error": False
              }

          return {
              "content": "Todos have been modified successfully. Ensure that you
  continue to use the todo list to track your progress. Please proceed with the
  current tasks if applicable",
              "is_error": False
          }

  Implementation Notes:
  - In-memory todo list (doesn't persist across agent restarts for MVP)
  - Validates task structure
  - Could enhance by persisting to file in workspace

  ---
  3.8 MCP Tool Integration

  Purpose: Execute custom MCP tools (e.g., BigQuery)

  class MCPToolProxy(BaseTool):
      """Proxy for MCP server tools"""

      def __init__(self, mcp_name: str, tool_name: str, tool_fn, schema: dict,
  workspace_dir: str):
          super().__init__(workspace_dir)
          self.mcp_name = mcp_name
          self.tool_name = tool_name
          self.tool_fn = tool_fn
          self._schema = schema

      @property
      def name(self) -> str:
          return f"mcp__{self.mcp_name}__{self.tool_name}"

      @property
      def schema(self) -> dict:
          # Convert MCP schema to Anthropic format
          return {
              "name": self.name,
              "description": self._schema.get("description", ""),
              "input_schema": self._schema.get("inputSchema", {})
          }

      async def execute(self, input: dict) -> dict:
          try:
              # Execute MCP tool function
              result = await self.tool_fn(input)

              # MCP tools return {"content": [...]} format
              # Anthropic expects string content
              if isinstance(result.get("content"), list):
                  content_text = "\n".join([
                      block.get("text", "") for block in result["content"]
                      if block.get("type") == "text"
                  ])
              else:
                  content_text = str(result.get("content", ""))

              return {
                  "content": content_text,
                  "is_error": False
              }
          except Exception as e:
              return {
                  "content": f"MCP tool error: {str(e)}",
                  "is_error": True
              }

  Usage in Agent:

  # In agent initialization
  def _register_mcp_servers(self, mcp_servers: dict):
      """Register MCP server tools"""
      for server_name, server in mcp_servers.items():
          for tool in server.tools:
              mcp_tool = MCPToolProxy(
                  mcp_name=server_name,
                  tool_name=tool.name,
                  tool_fn=tool.function,
                  schema=tool.schema,
                  workspace_dir=self.workspace_dir
              )
              self.tools.register(mcp_tool)

  ---
  4. ADDITIONAL FINDINGS & DESIGN CONSIDERATIONS

  4.1 System Prompt Adaptation

  Claude Code → Research Engineer Transformation

  Current Claude Code prompt targets:
  - Software engineers
  - Development tasks (debugging, PRs, code review)
  - Technical terminology

  New Research Engineer prompt should:
  - Target non-technical users (business analysts, researchers)
  - Focus on data analysis, insights, visualization
  - Use accessible language
  - Guide users through research questions

  Key Sections to Modify:

  # Research Engineer Agent System Prompt

  You are a **healthcare data research engineer** powered by Claude. You help
  non-technical users analyze prescription drug claims data using BigQuery.

  ## Your Capabilities

  You can:
  - Query large healthcare datasets (millions of prescription claims)
  - Analyze prescriber behavior and drug utilization patterns
  - Create visualizations and reports
  - Cluster and segment data
  - Perform statistical analysis

  ## Tone and Style

  - Use **plain English** (avoid jargon like "ETL", "schema", "ORM")
  - Explain technical concepts simply
  - Proactively suggest relevant analyses
  - Ask clarifying questions about research goals
  - Provide context and interpretation with results

  ## Research Workflow

  When a user asks a research question:
  1. **Clarify** the question if ambiguous
  2. **Query** BigQuery for relevant data
  3. **Analyze** the results (statistics, trends, patterns)
  4. **Visualize** key findings
  5. **Interpret** results in business context
  6. **Suggest** follow-up questions

  ## Examples

  ❌ BAD (too technical):
  "I'll join the rx_claims table on PRESCRIBER_NPI_NBR and aggregate by NDC..."

  ✅ GOOD (accessible):
  "I'll find all HUMIRA prescribers in California and count their prescriptions..."

  ---

  ## Available Tools

  You have access to:
  - **BigQuery**: Query prescription claims database
  - **Python**: Data analysis (pandas, matplotlib, seaborn, sklearn)
  - **File Management**: Save and read CSV files, create Python scripts
  - **Bash**: Run scripts and commands

  [Rest of Claude Code tool documentation...]

  4.2 Prompt Engineering Details

  Critical Changes:

  1. Remove git/PR/commit workflows (not relevant for research)
  2. Remove software engineering terminology
  3. Add research methodology guidance:
    - Ask clarifying questions about analysis goals
    - Suggest visualizations proactively
    - Provide statistical context (e.g., "This is statistically significant
  because...")
  4. Add example research flows:
  User: "Find top HUMIRA prescribers"
  Agent:
  1. Clarify: "In which state? Any specific time period?"
  2. Query: "I'll query all prescribers who wrote HUMIRA prescriptions..."
  3. Results: "Found 7,441 prescribers in California"
  4. Suggest: "Would you like me to cluster them by volume or analyze geographic
  distribution?"

  4.3 Error Handling & Resilience

  Critical Error Scenarios:

  1. BigQuery timeout (large queries)
    - Solution: Implement query timeout limits, suggest sampling
  2. File not found errors
    - Solution: Helpful error messages, suggest ls to explore workspace
  3. Tool execution failures
    - Solution: Retry logic for transient failures, clear error messages
  4. API rate limits (Anthropic)
    - Solution: Exponential backoff, queue management

  4.4 Testing Strategy

  Unit Tests (pytest):
  @pytest.mark.asyncio
  async def test_bash_tool_basic():
      tool = BashTool("/tmp/workspace")
      result = await tool.execute({"command": "echo 'hello'"})
      assert result["content"].strip() == "hello"
      assert result["is_error"] is False

  @pytest.mark.asyncio
  async def test_read_tool_with_offset():
      # Create test file
      with open("/tmp/workspace/test.txt", "w") as f:
          f.write("\n".join([f"line {i}" for i in range(100)]))

      tool = ReadTool("/tmp/workspace")
      result = await tool.execute({
          "file_path": "/tmp/workspace/test.txt",
          "offset": 10,
          "limit": 5
      })

      assert "11→line 10" in result["content"]
      assert "15→line 14" in result["content"]

  Integration Tests:
  @pytest.mark.asyncio
  async def test_agent_bigquery_workflow():
      agent = ResearchAgent(
          session_id="test",
          workspace_dir="/tmp/test_workspace",
          system_prompt=RESEARCH_PROMPT
      )

      # Simulate user query
      responses = []
      async for msg in agent.run("Find top 10 HUMIRA prescribers in California"):
          responses.append(msg)

      # Assert BigQuery tool was called
      assert any("mcp__bigquery__bigquery_query" in str(r) for r in responses)

      # Assert CSV file created
      assert os.path.exists("/tmp/test_workspace/prescribers.csv")

  Modal Sandbox Tests:
  - Deploy test function to Modal
  - Verify workspace persistence
  - Test streaming output
  - Verify session isolation

  4.5 MVP Implementation Scope

  Phase 1: Core Loop (Day 1)
  - ✅ Basic message loop with Anthropic SDK
  - ✅ Text streaming
  - ✅ Tool request parsing
  - ✅ Tool result handling

  Phase 2: Essential Tools (Day 2)
  - ✅ Bash tool
  - ✅ Read tool
  - ✅ Write tool
  - ✅ MCP tool proxy (BigQuery)

  Phase 3: Enhanced Tools (Day 3)
  - ✅ Edit tool
  - ✅ Glob tool
  - ✅ Grep tool
  - ✅ TodoWrite tool

  Phase 4: Integration & Testing (Day 4)
  - ✅ System prompt adaptation
  - ✅ Modal deployment
  - ✅ End-to-end testing
  - ✅ Error handling refinement

  Phase 5: Nice-to-Haves (Optional)
  - ❌ NotebookEdit (defer unless needed)
  - ❌ WebFetch (defer unless needed)
  - ❌ WebSearch (requires external API - defer)
  - ❌ Task/Agent tool (complex - defer)

  ---
  5. IMPLEMENTATION PLAN

  5.1 Starting Point

  File Structure:
  agent_v5/
  ├── __init__.py
  ├── __main__.py         # Entry point (modal run agent_v5/__main__.py)
  ├── agent.py            # ResearchAgent class
  ├── tools/
  │   ├── __init__.py
  │   ├── base.py         # BaseTool abstract class
  │   ├── registry.py     # ToolRegistry
  │   ├── bash.py         # BashTool
  │   ├── read.py         # ReadTool
  │   ├── write.py        # WriteTool
  │   ├── edit.py         # EditTool
  │   ├── glob.py         # GlobTool
  │   ├── grep.py         # GrepTool
  │   ├── todo.py         # TodoWriteTool
  │   └── mcp_proxy.py    # MCPToolProxy
  ├── system_prompt.md    # Research engineer prompt
  └── tests/
      ├── test_tools.py
      └── test_agent.py

  5.2 Development Steps

  Step 1: Create Base Tool Framework (30 min)
  # Create directory structure
  mkdir -p agent_v5/tools agent_v5/tests

  # Implement BaseTool and ToolRegistry
  # Test with mock tool

  Step 2: Implement Core Tools (2 hours)
  # Implement: Bash, Read, Write
  # Write unit tests for each
  pytest agent_v5/tests/test_tools.py::test_bash
  pytest agent_v5/tests/test_tools.py::test_read
  pytest agent_v5/tests/test_tools.py::test_write

  Step 3: Implement Agent Loop (2 hours)
  # Implement ResearchAgent class
  # Test message loop without tools
  # Add tool execution to loop
  # Test with Bash tool

  Step 4: Add MCP Integration (1 hour)
  # Implement MCPToolProxy
  # Connect BigQuery MCP server
  # Test end-to-end: user query → BigQuery → CSV

  Step 5: Enhanced Tools (2 hours)
  # Implement: Edit, Glob, Grep, TodoWrite
  # Write tests
  # Test integration with agent loop

  Step 6: System Prompt (1 hour)
  # Adapt Claude Code prompt to research engineer
  # Test tone and behavior
  # Iterate based on sample queries

  Step 7: Modal Deployment (1 hour)
  # Update main.py for Modal
  # Test workspace persistence
  # Test streaming output
  # Verify session isolation

  Step 8: End-to-End Testing (1 hour)
  # Run full research workflow:
  # - "Find top HUMIRA prescribers in California"
  # - "Cluster them by volume"
  # - "Create a visualization"
  # - Verify: CSV files, PNG files, correct results

  5.3 Testing Strategy

  Quick Verification Test (after each step):
  # Test immediately after implementing each component
  # Example: After implementing Bash tool
  python -m agent_v5.tools.bash  # Run tool's test main()

  Integration Test (after Step 4):
  # Run agent with simple query
  modal run agent_v5/__main__.py
  # Input: "List files in workspace"
  # Expected: Bash tool called, output streamed

  Full Workflow Test (after Step 7):
  modal run agent_v5/__main__.py
  # Input: "Find top 10 HUMIRA prescribers in California and save to CSV"
  # Expected:
  # 1. BigQuery tool called
  # 2. CSV file created in workspace
  # 3. Results summarized
  # 4. File persists after session

  5.4 Success Criteria

  ✅ Agent works without Claude Code SDK
  ✅ All tools functional (Bash, Read, Write, Edit, Glob, Grep, TodoWrite, MCP)
  ✅ Streaming output to local terminal
  ✅ Persistent workspace across messages
  ✅ Research-friendly prompt (non-technical tone)
  ✅ Full workflow works: query → analysis → visualization → saved files

  ---
  6. RISK MITIGATION

  Risk 1: Tool Schema Mismatches
  - Anthropic SDK has specific tool schema format
  - Mitigation: Validate schemas against Anthropic docs, test early

  Risk 2: Streaming Complexity
  - Async streaming + tool execution can deadlock
  - Mitigation: Use async for correctly, test streaming separately

  Risk 3: Workspace Permissions
  - Modal volume permissions might block file operations
  - Mitigation: Test file operations early, use correct volume mount

  Risk 4: MCP Integration Breaks
  - MCP tools might not work with our proxy
  - Mitigation: Test BigQuery tool first, ensure schema compatibility

  Risk 5: Prompt Doesn't Feel Research-Focused
  - Users might still get technical responses
  - Mitigation: Iterate on prompt, add few-shot examples, test with non-technical
  queries

  ---
  7. FINAL CONFIRMATION REQUEST

  This plan implements:

  1. ✅ Complete Claude Code replacement (no SDK dependency)
  2. ✅ All essential tools (Bash, Read, Write, Edit, Glob, Grep, TodoWrite, MCP)
  3. ✅ Research engineer prompt (non-technical, user-friendly)
  4. ✅ Modal integration (sandboxes, persistent workspace, streaming)
  5. ✅ Surgical MVP approach (core tools first, iterate)
  6. ✅ Testing strategy (unit, integration, E2E)

  DO YOU CONFIRM THIS PLAN?

  Once confirmed, I will:
  1. Start with Step 1 (base tool framework)
  2. Test immediately (unit tests for each tool)
  3. Build incrementally (core loop → tools → integration)
  4. Deploy to Modal (test in real sandbox environment)
  5. Iterate based on your feedback

  I am ready to execute with brilliance, diligence, and precision.