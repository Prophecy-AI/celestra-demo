# Agent V5 Implementation Plan

## Objective
Replace Claude Code SDK dependency with custom implementation while maintaining all functionality.

## Testing Strategy
- **Granular unit tests** for every component
- **Test immediately** after implementing each component
- **Commit after** every working increment
- **No end-to-end tests** until all components work individually

---

## Phase 1: Base Tool Framework

### 1.1 Create Directory Structure
```bash
agent_v5/
├── __init__.py
├── tools/
│   ├── __init__.py
│   ├── base.py           # BaseTool abstract class
│   └── registry.py       # ToolRegistry
└── tests/
    ├── __init__.py
    └── test_base.py
```

### 1.2 Implement BaseTool (agent_v5/tools/base.py)
```python
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
        """Return Anthropic API compatible tool schema"""
        pass

    @abstractmethod
    async def execute(self, input: dict) -> dict:
        """Execute tool and return {content: str, is_error: bool}"""
        pass
```

### 1.3 Implement ToolRegistry (agent_v5/tools/registry.py)
```python
class ToolRegistry:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.tools = {}

    def register(self, tool):
        self.tools[tool.name] = tool

    def get_schemas(self):
        return [tool.schema for tool in self.tools.values()]

    async def execute(self, tool_name: str, tool_input: dict):
        if tool_name not in self.tools:
            return {"content": f"Unknown tool: {tool_name}", "is_error": True}
        return await self.tools[tool_name].execute(tool_input)
```

### 1.4 Tests for Base Framework
**File: agent_v5/tests/test_base.py**
- Test 1: BaseTool is abstract and cannot be instantiated
- Test 2: Mock tool can be registered
- Test 3: Registry returns correct schemas
- Test 4: Registry executes tool correctly
- Test 5: Registry handles unknown tool gracefully

**Run:** `pytest agent_v5/tests/test_base.py -v`

**Commit:** `git commit -m "feat: implement base tool framework with tests"`

---

## Phase 2: Core Tools

### 2.1 Bash Tool (agent_v5/tools/bash.py)

**Implementation:**
- Schema with command, description, timeout parameters
- Execute shell command in workspace directory
- Timeout enforcement (default 120s, max 600s)
- Output truncation at 30k characters
- Error handling

**Tests (agent_v5/tests/test_bash.py):**
1. `test_bash_simple_command()` - Execute `echo "hello"`
2. `test_bash_with_cwd()` - Verify command runs in workspace_dir
3. `test_bash_timeout()` - Command that sleeps 5s with 1s timeout
4. `test_bash_output_truncation()` - Generate >30k chars, verify truncation
5. `test_bash_error_handling()` - Non-existent command
6. `test_bash_stderr_capture()` - Command with stderr output
7. `test_bash_multiline_output()` - Command with multiple lines

**Run:** `pytest agent_v5/tests/test_bash.py -v`

**Commit:** `git commit -m "feat: implement Bash tool with comprehensive tests"`

---

### 2.2 Read Tool (agent_v5/tools/read.py)

**Implementation:**
- Schema with file_path, offset, limit parameters
- Line numbering (cat -n format with arrow)
- Line truncation at 2000 characters
- Default 2000 line limit
- Empty file warning
- Handle absolute and relative paths

**Tests (agent_v5/tests/test_read.py):**
1. `test_read_simple_file()` - Read basic text file
2. `test_read_with_line_numbers()` - Verify cat -n format
3. `test_read_with_offset()` - Read from line 10
4. `test_read_with_limit()` - Read only 5 lines
5. `test_read_line_truncation()` - Line >2000 chars
6. `test_read_empty_file()` - Verify warning message
7. `test_read_file_not_found()` - Non-existent file
8. `test_read_relative_path()` - Relative to workspace
9. `test_read_absolute_path()` - Absolute path

**Run:** `pytest agent_v5/tests/test_read.py -v`

**Commit:** `git commit -m "feat: implement Read tool with comprehensive tests"`

---

### 2.3 Write Tool (agent_v5/tools/write.py)

**Implementation:**
- Schema with file_path, content parameters
- Create parent directories automatically
- Distinguish create vs overwrite in response
- Handle absolute and relative paths

**Tests (agent_v5/tests/test_write.py):**
1. `test_write_new_file()` - Create new file
2. `test_write_overwrite_file()` - Overwrite existing
3. `test_write_creates_directories()` - Parent dirs don't exist
4. `test_write_relative_path()` - Relative to workspace
5. `test_write_absolute_path()` - Absolute path
6. `test_write_empty_content()` - Write empty string
7. `test_write_large_content()` - Write >100kb content
8. `test_write_unicode()` - Unicode characters

**Run:** `pytest agent_v5/tests/test_write.py -v`

**Commit:** `git commit -m "feat: implement Write tool with comprehensive tests"`

---

## Phase 3: Enhanced Tools

### 3.1 Edit Tool (agent_v5/tools/edit.py)

**Implementation:**
- Schema with file_path, old_string, new_string, replace_all
- Exact string matching
- Uniqueness check (fail if multiple matches unless replace_all)
- Show snippet of edited region

**Tests (agent_v5/tests/test_edit.py):**
1. `test_edit_single_replacement()` - Replace unique string
2. `test_edit_replace_all()` - Replace multiple occurrences
3. `test_edit_string_not_found()` - Error when not found
4. `test_edit_multiple_matches_error()` - Error without replace_all
5. `test_edit_shows_snippet()` - Verify output shows context
6. `test_edit_file_not_found()` - Non-existent file
7. `test_edit_preserve_indentation()` - Exact string match

**Run:** `pytest agent_v5/tests/test_edit.py -v`

**Commit:** `git commit -m "feat: implement Edit tool with comprehensive tests"`

---

### 3.2 Glob Tool (agent_v5/tools/glob.py)

**Implementation:**
- Schema with pattern, path parameters
- Support ** for recursive matching
- Sort by modification time (most recent first)
- Return newline-separated paths

**Tests (agent_v5/tests/test_glob.py):**
1. `test_glob_simple_pattern()` - Find *.txt files
2. `test_glob_recursive()` - Pattern **/*.py
3. `test_glob_no_matches()` - Pattern with no results
4. `test_glob_sorted_by_mtime()` - Verify sort order
5. `test_glob_relative_path()` - Search in subdirectory
6. `test_glob_multiple_extensions()` - Pattern *.{py,txt}

**Run:** `pytest agent_v5/tests/test_glob.py -v`

**Commit:** `git commit -m "feat: implement Glob tool with comprehensive tests"`

---

### 3.3 Grep Tool (agent_v5/tools/grep.py)

**Implementation:**
- Use ripgrep (rg) subprocess
- Support all flags: -i, -n, -A, -B, -C, --glob, --type
- Three output modes: content, files_with_matches, count
- Multiline support
- Head limit for truncation

**Tests (agent_v5/tests/test_grep.py):**
1. `test_grep_simple_pattern()` - Find "test" in files
2. `test_grep_case_insensitive()` - -i flag
3. `test_grep_with_line_numbers()` - -n flag
4. `test_grep_context_lines()` - -A, -B, -C flags
5. `test_grep_glob_filter()` - Search only *.py
6. `test_grep_type_filter()` - --type py
7. `test_grep_output_modes()` - Test all 3 modes
8. `test_grep_no_matches()` - Pattern not found
9. `test_grep_multiline()` - Multiline pattern
10. `test_grep_head_limit()` - Truncate results

**Run:** `pytest agent_v5/tests/test_grep.py -v`

**Commit:** `git commit -m "feat: implement Grep tool with comprehensive tests"`

---

## Phase 4: Agent Loop

### 4.1 Implement ResearchAgent (agent_v5/agent.py)

**Implementation:**
- Initialize with session_id, workspace_dir, system_prompt
- Conversation history management
- Anthropic API streaming integration
- Tool execution loop
- Parse streaming events (text_delta, tool_use)
- Yield messages to caller

**Tests (agent_v5/tests/test_agent.py):**
1. `test_agent_initialization()` - Creates agent with tools
2. `test_agent_simple_text_response()` - No tool use
3. `test_agent_streaming()` - Text chunks yielded
4. `test_agent_tool_execution()` - Uses Bash tool
5. `test_agent_multiple_tools()` - Uses multiple tools in sequence
6. `test_agent_conversation_history()` - History maintained correctly
7. `test_agent_error_handling()` - Tool returns error
8. `test_agent_max_turns()` - Stops after max iterations

**Run:** `pytest agent_v5/tests/test_agent.py -v`

**Commit:** `git commit -m "feat: implement ResearchAgent with message loop and tests"`

---

## Phase 5: MCP Integration

### 5.1 Implement MCPToolProxy (agent_v5/tools/mcp_proxy.py)

**Implementation:**
- Wrap MCP tool function
- Convert MCP schema to Anthropic format
- Name format: `mcp__{server}__{tool}`
- Handle MCP response format → Anthropic format

**Tests (agent_v5/tests/test_mcp_proxy.py):**
1. `test_mcp_proxy_name_format()` - Verify naming convention
2. `test_mcp_proxy_schema_conversion()` - MCP → Anthropic schema
3. `test_mcp_proxy_execution()` - Execute mock MCP tool
4. `test_mcp_proxy_response_format()` - Convert response
5. `test_mcp_proxy_error_handling()` - MCP tool raises error

**Run:** `pytest agent_v5/tests/test_mcp_proxy.py -v`

**Commit:** `git commit -m "feat: implement MCP tool proxy with tests"`

---

## Phase 6: TodoWrite Tool

### 6.1 Implement TodoWriteTool (agent_v5/tools/todo.py)

**Implementation:**
- Schema with todos array
- In-memory todo list
- Validate: exactly one in_progress task
- Return success message

**Tests (agent_v5/tests/test_todo.py):**
1. `test_todo_empty_list()` - Initialize with no todos
2. `test_todo_add_tasks()` - Add pending tasks
3. `test_todo_mark_in_progress()` - One task in progress
4. `test_todo_multiple_in_progress_warning()` - Validation error
5. `test_todo_complete_task()` - Mark task completed
6. `test_todo_required_fields()` - Validate schema

**Run:** `pytest agent_v5/tests/test_todo.py -v`

**Commit:** `git commit -m "feat: implement TodoWrite tool with tests"`

---

## Phase 7: Integration with Modal

### 7.1 Create New Main Entry Point (agent_v5/main.py)

**Implementation:**
- Copy from agent_v4/main.py
- Replace ClaudeSDKClient with ResearchAgent
- Keep BigQuery MCP integration
- Keep Modal function structure
- Keep session isolation

**Tests (manual for now):**
1. Deploy to Modal: `modal deploy agent_v5/main.py`
2. Test simple query: "List files in workspace"
3. Test BigQuery tool: "Query rx_claims for top 10 drugs"
4. Test persistence: Save CSV, then read it in next message

**Commit:** `git commit -m "feat: integrate ResearchAgent with Modal, replace Claude SDK"`

---

## Phase 8: System Prompt

### 8.1 Research Engineer Prompt (agent_v5/system_prompt.md)

**Content:**
- Target non-technical users
- Focus on data analysis workflows
- Plain English (no jargon)
- Proactive suggestions
- Example workflows

**Tests (manual):**
1. Ask research question in plain language
2. Verify agent responds in accessible way
3. Verify agent suggests follow-ups
4. Compare responses to original Claude Code tone

**Commit:** `git commit -m "feat: adapt system prompt for research engineer persona"`

---

## Testing Requirements

### Every tool MUST have tests for:
1. ✅ Happy path (basic functionality)
2. ✅ Edge cases (empty input, large input, unicode)
3. ✅ Error cases (file not found, permission denied, timeout)
4. ✅ Schema validation (correct Anthropic format)
5. ✅ Output format (matches expected structure)

### Test Execution Order:
1. Run unit tests for each tool immediately after implementation
2. Run all tool tests together: `pytest agent_v5/tests/test_*.py -v`
3. Run agent tests after loop implementation
4. Run MCP tests after proxy implementation
5. Manual Modal tests after integration

---

## Success Criteria

✅ All unit tests pass
✅ Agent works without Claude Code SDK
✅ All tools functional (Bash, Read, Write, Edit, Glob, Grep, TodoWrite, MCP)
✅ Streaming output works
✅ Persistent workspace works
✅ BigQuery integration works
✅ System prompt adapted for research users

---

## Risk Mitigation

1. **Tool schema errors**: Validate against Anthropic docs before implementing
2. **Async issues**: Test streaming separately from tool execution
3. **Modal permissions**: Test file operations early in sandbox
4. **MCP compatibility**: Test BigQuery tool first with mock data

---

## Commit Strategy

- Commit after each tool is implemented and tested
- Commit message format: `feat: implement [Tool] with comprehensive tests`
- Never commit failing tests
- Never commit untested code
