# Building Autonomous Agents: A Complete Framework Guide

> **A comprehensive guide to designing, building, and deploying production-ready autonomous AI agents**

---

## Table of Contents

1. [Introduction to Autonomous Agents](#introduction-to-autonomous-agents)
2. [Core Architecture Patterns](#core-architecture-patterns)
3. [The Agentic Loop](#the-agentic-loop)
4. [Tool System Design](#tool-system-design)
5. [Security & Sandboxing](#security--sandboxing)
6. [Observability & Debugging](#observability--debugging)
7. [Quality Evaluation](#quality-evaluation)
8. [Deployment Strategies](#deployment-strategies)
9. [Example: Healthcare Research Agent](#example-healthcare-research-agent)
10. [Building Your Own Agent](#building-your-own-agent)
11. [Advanced Patterns](#advanced-patterns)
12. [Best Practices](#best-practices)

---

## Introduction to Autonomous Agents

### What Are Autonomous Agents?

Autonomous agents are AI systems that can:
- **Plan** multi-step solutions to complex problems
- **Execute** actions through tools/APIs
- **Adapt** based on feedback and intermediate results
- **Reason** about their progress and next steps
- **Persist** context across multiple interactions

Unlike simple chatbots, autonomous agents have **agency** – they can take actions in the world.

### Key Characteristics

```
Traditional Chatbot:
  User: "What's the weather?"
  Bot: "I don't have access to weather data"
  [End of conversation]

Autonomous Agent:
  User: "What's the weather?"
  Agent: [Uses weather API tool]
  Agent: "Currently 72°F and sunny in San Francisco"
  User: "Should I bring an umbrella this week?"
  Agent: [Uses weather forecast tool]
  Agent: "Yes, rain expected Thursday-Friday"
  [Context maintained, proactive tool use]
```

### Why Build Custom Agents?

**Instead of using pre-built SDKs:**
- ✅ **Full control** over agent behavior and tool execution
- ✅ **Domain-specific optimization** (e.g., healthcare, finance, engineering)
- ✅ **Security requirements** (sandbox environments, audit trails)
- ✅ **Custom tools** specific to your use case
- ✅ **Testability** (unit tests, integration tests, e2e tests)
- ✅ **Observability** (track costs, latency, errors)

---

## Core Architecture Patterns

### Pattern 1: Agent-Tool-Registry Architecture

This is the foundation of most autonomous agents:

```
┌─────────────────────────────────────────────────────────────────┐
│                         USER INPUT                               │
│                    "Solve this problem"                          │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                    AGENT ORCHESTRATOR                            │
│  - Maintains conversation history                                │
│  - Calls LLM with available tools                                │
│  - Decides when to use tools vs respond                          │
│  - Loops until task complete                                     │
└───────────┬──────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TOOL REGISTRY                                 │
│  - Registers available tools                                     │
│  - Validates tool inputs (security, types)                       │
│  - Executes tools safely                                         │
│  - Returns results to agent                                      │
└───────────┬──────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    TOOLS (Extensible)                            │
│  File I/O  │  Code Exec  │  API Calls  │  Database  │  Custom   │
└─────────────────────────────────────────────────────────────────┘
            │
            ▼
┌─────────────────────────────────────────────────────────────────┐
│                    ENVIRONMENT / WORKSPACE                       │
│  Sandboxed execution environment for agent operations            │
└─────────────────────────────────────────────────────────────────┘
```

### Pattern 2: Three-Layer Architecture

**Layer 1: Interface Layer**
- CLI, web UI, API endpoints
- Handles user I/O
- Manages sessions
- Example: `cli.py`, `main.py`

**Layer 2: Agent Layer**
- Orchestrates the agentic loop
- Manages conversation state
- Decides on tool usage
- Streams responses
- Example: `ResearchAgent` class

**Layer 3: Tool Layer**
- Individual capabilities (read file, run code, query DB)
- Validated and sandboxed
- Reusable across agents
- Example: `BashTool`, `ReadTool`, etc.

### Pattern 3: Workspace Isolation

**Problem:** Multiple users/sessions need isolation

**Solution:** Each session gets isolated workspace

```
workspace/
  ├── session_abc123/          ← User A's sandbox
  │   ├── data.csv
  │   ├── analysis.py
  │   └── results/
  ├── session_def456/          ← User B's sandbox
  │   ├── report.txt
  │   └── scripts/
  └── session_ghi789/          ← User C's sandbox
      └── output.json
```

**Benefits:**
- Security: Users can't access each other's data
- Cleanup: Delete session = delete directory
- Debugging: Inspect workspace after session
- Persistence: Files survive across turns

---

## The Agentic Loop

### Core Concept

The **agentic loop** is the heart of an autonomous agent. It's a cycle of:
1. Receive user input
2. Reason about what to do
3. Execute tools if needed
4. Reflect on results
5. Repeat until task complete

### Implementation Pattern

```python
class AutonomousAgent:
    def __init__(self, system_prompt, tools):
        self.system_prompt = system_prompt
        self.tools = ToolRegistry(tools)
        self.conversation_history = []
        self.llm_client = LLMClient()  # Anthropic, OpenAI, etc.

    async def run(self, user_message):
        # Add user message to history
        self.conversation_history.append({
            "role": "user",
            "content": user_message
        })

        # Main agentic loop
        while True:
            # 1. Call LLM with tools and conversation history
            response = await self.llm_client.complete(
                messages=self.conversation_history,
                tools=self.tools.get_schemas(),
                system=self.system_prompt
            )

            # 2. Stream text to user (if any)
            yield response.text

            # 3. Check if LLM wants to use tools
            if not response.tool_uses:
                break  # Task complete!

            # 4. Execute tools
            tool_results = []
            for tool_use in response.tool_uses:
                result = await self.tools.execute(
                    tool_use.name,
                    tool_use.input
                )
                tool_results.append(result)

            # 5. Add results to conversation history
            self.conversation_history.append({
                "role": "assistant",
                "content": response.full_content
            })
            self.conversation_history.append({
                "role": "user",
                "content": tool_results
            })

            # 6. Loop continues - LLM sees results and decides next step
```

### Why This Pattern Works

**Advantages:**
- LLM decides when it needs tools vs when to respond
- Multi-step reasoning (chain of thought)
- Error recovery (tool fails → LLM sees error → tries different approach)
- Flexible (works for simple and complex tasks)

**Key Design Decisions:**

1. **Streaming responses**: User sees progress in real-time
2. **Tool validation**: Security checks before execution
3. **Conversation history**: Maintains context across turns
4. **Loop termination**: LLM decides when task is done

---

## Tool System Design

### Base Tool Interface

Every tool should implement this interface:

```python
from abc import ABC, abstractmethod
from typing import Dict

class BaseTool(ABC):
    """Abstract base for all tools"""

    def __init__(self, workspace_dir: str):
        """Initialize with workspace directory"""
        self.workspace_dir = workspace_dir
        self._prehook = None  # For validation

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool identifier (e.g., 'ReadFile', 'ExecuteCode')"""
        pass

    @property
    @abstractmethod
    def schema(self) -> Dict:
        """LLM-compatible schema describing tool usage"""
        return {
            "name": self.name,
            "description": "What this tool does",
            "input_schema": {
                "type": "object",
                "properties": {
                    "param": {
                        "type": "string",
                        "description": "Parameter description"
                    }
                },
                "required": ["param"]
            }
        }

    async def prehook(self, input: Dict):
        """Validate/transform input before execution"""
        if self._prehook:
            await self._prehook(input)

    @abstractmethod
    async def execute(self, input: Dict) -> Dict:
        """Execute the tool"""
        return {
            "content": "Tool output",
            "is_error": False
        }
```

### Tool Categories

**1. File System Tools**
- **Read**: Read file contents
- **Write**: Create/overwrite files
- **Edit**: Modify existing files
- **Glob**: Find files by pattern
- **Grep**: Search file contents

**2. Execution Tools**
- **Bash**: Execute shell commands
- **Python**: Run Python code
- **Docker**: Execute in containers

**3. Data Tools**
- **SQL Query**: Execute database queries
- **API Call**: HTTP requests
- **Embedding**: Vector search

**4. Meta Tools**
- **TodoList**: Task planning
- **Delegate**: Sub-agent spawning
- **Memory**: Long-term storage

### Tool Registry Pattern

Centralize tool management:

```python
class ToolRegistry:
    def __init__(self, workspace_dir: str):
        self.workspace_dir = workspace_dir
        self.tools: Dict[str, BaseTool] = {}

    def register(self, tool: BaseTool):
        """Add tool to registry"""
        self.tools[tool.name] = tool

    def set_prehook(self, tool_name: str, hook_fn):
        """Add validation hook to specific tool"""
        self.tools[tool_name]._prehook = hook_fn

    def get_schemas(self) -> List[Dict]:
        """Get all tool schemas for LLM"""
        return [tool.schema for tool in self.tools.values()]

    async def execute(self, tool_name: str, input: Dict) -> Dict:
        """Execute tool with validation"""
        if tool_name not in self.tools:
            return {"content": f"Unknown tool: {tool_name}", "is_error": True}

        tool = self.tools[tool_name]

        # Run prehook (validation)
        try:
            await tool.prehook(input)
        except Exception as e:
            return {"content": str(e), "is_error": True}

        # Execute
        return await tool.execute(input)
```

### Example Tool Implementation

```python
class BashTool(BaseTool):
    """Execute shell commands in workspace"""

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def schema(self) -> Dict:
        return {
            "name": "Bash",
            "description": "Execute shell commands in workspace directory",
            "input_schema": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "Shell command to execute"
                    },
                    "timeout": {
                        "type": "number",
                        "description": "Timeout in milliseconds (max 600000)"
                    }
                },
                "required": ["command"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        command = input["command"]
        timeout_s = input.get("timeout", 120000) / 1000

        try:
            process = await asyncio.create_subprocess_shell(
                f"cd {self.workspace_dir} && {command}",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            stdout, stderr = await asyncio.wait_for(
                process.communicate(),
                timeout=timeout_s
            )

            output = stdout.decode() + stderr.decode()

            return {
                "content": output,
                "is_error": process.returncode != 0
            }
        except asyncio.TimeoutError:
            return {
                "content": f"Command timed out after {timeout_s}s",
                "is_error": True
            }
```

### MCP Tool Integration

**Problem:** External tools (APIs, databases) have different interfaces

**Solution:** Model Context Protocol (MCP) wrapper

```python
class MCPToolProxy(BaseTool):
    """Wrap MCP server tools for use in agent"""

    def __init__(self, mcp_name: str, tool_name: str,
                 tool_fn: Callable, mcp_schema: Dict, workspace_dir: str):
        super().__init__(workspace_dir)
        self.mcp_name = mcp_name
        self.tool_name = tool_name
        self.tool_fn = tool_fn
        self.mcp_schema = mcp_schema

    @property
    def name(self) -> str:
        # Namespace: mcp__bigquery__query
        return f"mcp__{self.mcp_name}__{self.tool_name}"

    @property
    def schema(self) -> Dict:
        # Convert MCP schema to tool schema
        return {
            "name": self.name,
            "description": self.mcp_schema["description"],
            "input_schema": self.mcp_schema["inputSchema"]
        }

    async def execute(self, input: Dict) -> Dict:
        result = await self.tool_fn(input)
        return {"content": result, "is_error": False}
```

---

## Security & Sandboxing

### Threat Model

**What we protect against:**
- Workspace escape (accessing files outside sandbox)
- Data exfiltration (reading sensitive files)
- Code injection (malicious commands)
- Resource exhaustion (infinite loops, memory bombs)

### Path Validation Pattern

Prevent directory traversal attacks:

```python
class PathValidator:
    """Validate paths stay within workspace boundaries"""

    def __init__(self, workspace_dir: str):
        self.workspace_dir = os.path.realpath(workspace_dir)

    def validate(self, path: str, operation: str = "access") -> str:
        """
        Validate and normalize path

        Returns: Absolute path within workspace
        Raises: SecurityError if path escapes workspace
        """
        # Handle relative paths
        if not path.startswith('/'):
            resolved = os.path.realpath(
                os.path.join(self.workspace_dir, path)
            )
        else:
            resolved = os.path.realpath(path)

        # Check if within workspace
        if not resolved.startswith(self.workspace_dir + os.sep):
            raise SecurityError(
                f"Access denied: {operation} outside workspace. "
                f"Path: {path} -> {resolved}"
            )

        return resolved
```

**Attacks blocked:**
- `../../../etc/passwd` → SecurityError
- `/etc/passwd` → SecurityError
- `../../secrets.txt` → SecurityError
- Symlinks outside workspace → SecurityError

### Prehook Pattern

Inject validation before tool execution:

```python
def create_path_validation_prehook(workspace_dir: str):
    """Factory: Create validation hook for file tools"""
    validator = PathValidator(workspace_dir)

    async def prehook(input: Dict):
        # Validate all path parameters
        for param in ["file_path", "path"]:
            if param in input:
                # Normalize in-place
                input[param] = validator.validate(input[param])

    return prehook

# Usage:
agent = AutonomousAgent(...)
path_hook = create_path_validation_prehook(workspace_dir)

# Apply to all file tools
agent.tools.set_prehook("Read", path_hook)
agent.tools.set_prehook("Write", path_hook)
agent.tools.set_prehook("Edit", path_hook)
```

### Execution Sandboxing

**Level 1: Process isolation**
```python
# Run in separate process with resource limits
process = subprocess.Popen(
    command,
    cwd=workspace_dir,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    preexec_fn=set_resource_limits  # CPU, memory limits
)
```

**Level 2: Container isolation**
```python
# Run in Docker container
docker run \
  --rm \
  --network none \
  --cpus=1 \
  --memory=512m \
  --read-only \
  -v workspace:/workspace \
  python:3.11 \
  python /workspace/script.py
```

**Level 3: VM isolation (Modal, AWS Lambda)**
```python
# Each agent run in isolated VM
@modal.function(
    image=modal.Image.debian_slim(),
    timeout=600,
    cpu=2,
    memory=2048
)
def agent_turn(session_id, user_message):
    # Fully isolated execution
    agent = AutonomousAgent(...)
    return agent.run(user_message)
```

### Security Checklist

- [ ] Path validation for all file operations
- [ ] Timeout limits on all tool executions
- [ ] Resource limits (CPU, memory, disk)
- [ ] Network restrictions (whitelist domains)
- [ ] Input validation (schema validation)
- [ ] Output sanitization (prevent prompt injection)
- [ ] Audit logging (who did what when)
- [ ] Rate limiting (prevent abuse)

---

## Observability & Debugging

### Three Levels of Observability

**Level 1: Debug Logging (Development)**

Ultra-minimal overhead for development:

```python
# debug.py
import os, time

_DEBUG = os.getenv("DEBUG") == "1"

def log(message: str, level: int = 0):
    """Log if DEBUG=1. level: 0=info, 1=success, 2=error"""
    if not _DEBUG:
        return

    colors = {0: "\033[2m", 1: "\033[32m", 2: "\033[31m"}
    reset = "\033[0m"
    timestamp = time.strftime('%H:%M:%S')

    print(f"{colors[level]}[{timestamp}] {message}{reset}", flush=True)

# Usage:
log("→ Agent.run()")
log("✓ Tool executed successfully", 1)
log("✗ Error occurred", 2)
```

```bash
# Enable debug output
DEBUG=1 python agent.py

# Output:
# [12:34:56] → Agent.run(session=abc123)
# [12:34:57] → ExecuteSQL(SELECT * FROM...)
# [12:34:58] ✓ ExecuteSQL: 1234 rows
# [12:34:59] ✓ Agent.run complete
```

**Level 2: Structured Logging (Production)**

```python
import structlog

logger = structlog.get_logger()

# In agent code:
logger.info("tool_execution",
    session_id=session_id,
    tool_name=tool_name,
    duration_ms=duration,
    success=not is_error
)
```

**Level 3: LLM Observability (Langfuse, Weights & Biases)**

Track LLM calls, costs, and quality:

```python
from langfuse import Langfuse

langfuse = Langfuse(
    public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
    secret_key=os.getenv("LANGFUSE_SECRET_KEY")
)

# Wrap agent with tracing
@langfuse.observe()
async def agent_run(user_message):
    # All LLM calls automatically tracked:
    # - Input tokens
    # - Output tokens
    # - Cost ($)
    # - Latency (ms)
    # - Tool uses
    return await agent.run(user_message)
```

**What gets tracked:**
- 📊 Token usage per request
- 💰 Cost per session
- ⏱️ Latency breakdown
- 🔧 Tool execution traces
- ❌ Error rates and types
- 📈 Quality metrics (if evals enabled)

### Debug Workflow

**1. Enable debug logging:**
```bash
DEBUG=1 python cli.py
```

**2. Check workspace:**
```bash
# Inspect intermediate files
ls -la workspace/abc123/

# Check tool outputs
cat workspace/abc123/debug.log
```

**3. Inspect conversation history:**
```python
# Add to agent
def dump_history(self):
    import json
    with open(f"{self.workspace_dir}/conversation.json", "w") as f:
        json.dump(self.conversation_history, f, indent=2)
```

**4. Use observability dashboard:**
- Go to Langfuse dashboard
- Filter by session_id
- See full trace with timing

---

## Quality Evaluation

### Why Evaluate Agents?

**Problems with autonomous agents:**
- Can hallucinate facts
- May write incorrect code
- Might misinterpret user intent
- Could make inefficient decisions

**Solution: Automated evaluation**

### Evaluation Pattern

```python
from abc import ABC, abstractmethod

class BaseEvaluator(ABC):
    """Base class for all evaluators"""

    @property
    @abstractmethod
    def name(self) -> str:
        """Evaluator name (e.g., 'hallucination', 'code_quality')"""
        pass

    @property
    @abstractmethod
    def prompt_template(self) -> str:
        """Evaluation prompt for LLM judge"""
        pass

    async def evaluate(self, data: Dict, llm_client) -> Dict:
        """
        Run evaluation

        Args:
            data: Context for evaluation (code, answer, etc.)
            llm_client: LLM for judging (e.g., o3, GPT-4)

        Returns:
            {"score": 0-100, "passed": bool, "reasoning": str}
        """
        # Fill template with data
        prompt = self.prompt_template.format(**data)

        # Use strong model for evaluation
        response = await llm_client.complete(
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0  # Deterministic
        )

        # Parse structured output
        return self._parse_result(response.text)

    @abstractmethod
    def _parse_result(self, text: str) -> Dict:
        """Parse LLM response into structured result"""
        pass
```

### Common Evaluators

**1. Hallucination Detection**

```python
class HallucinationEvaluator(BaseEvaluator):
    """Check if agent's claims are supported by data"""

    @property
    def name(self) -> str:
        return "hallucination"

    @property
    def prompt_template(self) -> str:
        return """Check if the agent's answer is supported by the data:

Agent Answer: {answer}
Source Data: {data}

Verify:
1. All numerical claims are accurate
2. All facts are present in source data
3. No invented information
4. No misinterpretations

Respond ONLY with valid JSON:
{{
  "score": <0-100>,
  "passed": <true/false>,
  "hallucinations": ["claim1", "claim2"],
  "reasoning": "..."
}}"""

    def _parse_result(self, text: str) -> Dict:
        return json.loads(text)
```

**2. Code Quality**

```python
class CodeEvaluator(BaseEvaluator):
    """Verify generated code correctness"""

    @property
    def prompt_template(self) -> str:
        return """Evaluate generated code:

Code: {code}
Purpose: {purpose}

Check:
1. Syntax correctness
2. Logic correctness
3. Edge case handling
4. Best practices
5. Security issues

Respond ONLY with valid JSON:
{{
  "score": <0-100>,
  "passed": <true/false>,
  "issues": ["issue1", "issue2"],
  "reasoning": "..."
}}"""
```

**3. Answer Quality**

```python
class AnswerEvaluator(BaseEvaluator):
    """Check if answer addresses question"""

    @property
    def prompt_template(self) -> str:
        return """Evaluate answer quality:

Question: {question}
Answer: {answer}

Check:
1. Does answer address the question?
2. Is answer complete?
3. Is answer clear and well-structured?
4. Are insights actionable?

Respond ONLY with valid JSON:
{{
  "score": <0-100>,
  "passed": <true/false>,
  "issues": [],
  "reasoning": "..."
}}"""
```

### Evaluation Runner

Fire-and-forget evaluation (doesn't block agent):

```python
class EvalRunner:
    """Orchestrate async evals"""

    def __init__(self, session_id: str, workspace_dir: str):
        self.session_id = session_id
        self.workspace_dir = workspace_dir
        self.enabled = os.getenv("EVALS_ENABLED") == "1"
        self.llm_client = LLMClient() if self.enabled else None
        self.evals_dir = Path(workspace_dir) / ".evals"

    def submit(self, eval_type: str, data: Dict):
        """Submit eval asynchronously (non-blocking)"""
        if not self.enabled:
            return

        # Fire and forget
        asyncio.create_task(self._run_eval(eval_type, data))

    async def _run_eval(self, eval_type: str, data: Dict):
        try:
            # Get evaluator
            evaluator = self._get_evaluator(eval_type)

            # Run evaluation
            result = await evaluator.evaluate(data, self.llm_client)

            # Save result
            timestamp = int(time.time())
            result_file = self.evals_dir / f"{eval_type}_{timestamp}.json"
            result_file.write_text(json.dumps({
                "eval_type": eval_type,
                "data": data,
                "result": result,
                "timestamp": timestamp
            }, indent=2))
        except Exception as e:
            log(f"Eval {eval_type} failed: {e}", 2)
```

### Integration Pattern

```python
class AutonomousAgent:
    def __init__(self, ...):
        # ... existing code ...
        self.evals = EvalRunner(session_id, workspace_dir)

    async def run(self, user_message):
        # ... main loop ...

        # After tool execution
        if tool_name == "ExecuteSQL":
            self.evals.submit("sql", {
                "sql": tool_input["query"],
                "context": "User requested analysis"
            })

        # After final response
        if not tool_uses:
            self.evals.submit("answer", {
                "question": user_message,
                "answer": final_text,
                "context": "Session complete"
            })
```

---

## Deployment Strategies

### Strategy 1: Local Development

**Best for:** Prototyping, testing, debugging

```python
# cli.py
import asyncio
from agent import AutonomousAgent

async def main():
    session_id = str(uuid.uuid4())[:8]
    workspace_dir = f"./workspace/{session_id}"
    Path(workspace_dir).mkdir(parents=True, exist_ok=True)

    agent = AutonomousAgent(
        session_id=session_id,
        workspace_dir=workspace_dir,
        system_prompt=SYSTEM_PROMPT
    )

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break

        async for message in agent.run(user_input):
            if message["type"] == "text_delta":
                print(message["text"], end="", flush=True)
        print()

if __name__ == "__main__":
    asyncio.run(main())
```

**Pros:**
- Fast iteration
- Easy debugging
- Direct file access
- No deployment overhead

**Cons:**
- Not secure (no sandbox)
- Single user
- Manual scaling

### Strategy 2: Serverless (Modal, AWS Lambda)

**Best for:** Production, auto-scaling, multi-user

```python
# main.py
import modal

app = modal.App("autonomous-agent")

# Build container image
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ripgrep")  # For grep tool
    .pip_install("anthropic", "polars", "pyarrow")
    .add_local_python_source("agent_v5")
    .add_local_python_source("security")
    .add_local_python_source("observability")
)

# Persistent storage
workspace_volume = modal.Volume.from_name(
    "agent-workspaces",
    create_if_missing=True
)

@app.function(
    image=image,
    volumes={"/workspace": workspace_volume},
    timeout=600,
    cpu=2,
    memory=4096,
    secrets=[modal.Secret.from_dotenv()]
)
async def agent_turn(session_id: str, user_message: str):
    """Execute one agent turn in isolated environment"""
    from agent import AutonomousAgent

    session_dir = f"/workspace/{session_id}"
    Path(session_dir).mkdir(exist_ok=True, parents=True)

    agent = AutonomousAgent(
        session_id=session_id,
        workspace_dir=session_dir,
        system_prompt=SYSTEM_PROMPT
    )

    async for message in agent.run(user_message):
        yield message

    # Persist workspace
    workspace_volume.commit()

@app.local_entrypoint()
def chat():
    """Local CLI that calls Modal function"""
    session_id = str(uuid.uuid4())[:8]

    while True:
        user_input = input("You: ")
        if user_input.lower() == 'exit':
            break

        for message in agent_turn.remote_gen(session_id, user_input):
            if message.get("type") == "text_delta":
                print(message["text"], end="", flush=True)
        print()
```

**Deployment:**
```bash
# Deploy to Modal cloud
modal deploy main.py

# Or run locally → Modal
modal run main.py
```

**Pros:**
- Fully isolated (security)
- Auto-scaling
- Pay-per-use
- Multi-user support
- Managed infrastructure

**Cons:**
- Cold start latency
- Complexity
- Vendor lock-in

---

## Example: Healthcare Research Agent

> **Real-world example of autonomous agent for healthcare data analysis**

### Domain Context

**Problem:** Healthcare analysts need to query complex databases, analyze data, and generate insights – but SQL and Python are barriers.

**Solution:** Natural language agent that:
- Understands healthcare terminology
- Queries BigQuery databases
- Analyzes data with Python/Polars
- Creates visualizations
- Explains findings in plain English

### System Prompt Design

```python
SYSTEM_PROMPT = """You are a healthcare data research engineer with direct BigQuery access.

**Available Datasets:**

1. RX_CLAIMS (Prescription Data)
   - PRESCRIBER_NPI_NBR: Prescriber's NPI
   - NDC_DRUG_NM: Drug name
   - PRESCRIBER_NPI_STATE_CD: State
   - SERVICE_DATE_DD: Fill date
   - DISPENSED_QUANTITY_VAL: Quantity

2. MED_CLAIMS (Medical Claims)
   - PRIMARY_HCP: Provider identifier
   - condition_label: Diagnosis/condition
   - STATEMENT_FROM_DD: Service date
   - CLAIM_CHARGE_AMT: Charge amount

3. PROVIDER_PAYMENTS (Healthcare Provider Payments)
   - npi_number: National Provider Identifier
   - associated_product: Associated product
   - total_payment_amount: Total payment amount

4. PROVIDERS_BIO (Provider Biographical)
   - npi_number: National Provider Identifier
   - specialty: Medical specialty
   - education: Educational background

**Your Tools:**
- mcp__bigquery__bigquery_query: Execute SQL and save results to CSV
- Read: Read files from workspace
- Write: Create Python scripts
- Bash: Execute scripts and commands
- Glob: Find files by pattern
- Grep: Search file contents

**Research Workflow:**
1. Understand the research question
2. Query BigQuery for relevant data (can join tables)
3. Analyze with Python/Polars if needed
4. Present findings clearly
5. Suggest follow-up analyses

**Guidelines:**
- Use plain English when explaining results
- Suggest follow-up analyses proactively
- Save intermediate results as CSV files
- Create visualizations when helpful
- Join tables when richer insights are needed

Current date: 2025-10-08"""
```

### Domain-Specific Tools

**BigQuery Tool (via MCP):**

```python
def create_bigquery_tool(workspace_dir, gcp_project, gcp_credentials):
    """Factory for BigQuery tool"""

    async def bigquery_query_tool(args):
        # 1. Execute SQL on BigQuery
        client = bigquery.Client(
            project=gcp_project,
            credentials=gcp_credentials
        )
        query_job = client.query(args["sql"])
        results = query_job.result()

        # 2. Convert to Polars (faster than Pandas)
        arrow_table = results.to_arrow(create_bqstorage_client=False)
        df = pl.from_arrow(arrow_table)

        # 3. Save to workspace as CSV
        csv_path = Path(workspace_dir) / f"{args['dataset_name']}.csv"
        df.write_csv(str(csv_path))

        # 4. Return preview
        return {
            "content": [{
                "type": "text",
                "text": f"Saved {df.shape[0]:,} rows to {csv_path}\n\n{df.head(10)}"
            }]
        }

    # Wrap with MCP proxy
    return MCPToolProxy(
        mcp_name="bigquery",
        tool_name="bigquery_query",
        tool_fn=bigquery_query_tool,
        mcp_schema={
            "description": "Execute SQL on BigQuery healthcare datasets and save to workspace",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL query to execute"
                    },
                    "dataset_name": {
                        "type": "string",
                        "description": "Name for CSV file (without extension)"
                    },
                    "description": {
                        "type": "string",
                        "description": "Brief description of what this query does"
                    }
                },
                "required": ["sql", "dataset_name", "description"]
            }
        },
        workspace_dir=workspace_dir
    )
```

### Example Interaction

```
User: Find the top 10 prescribers of HUMIRA in California

Agent: I'll query the rx_claims table for this analysis.

🔧 [Tool: mcp__bigquery__bigquery_query]
Input: {
  "sql": "SELECT PRESCRIBER_NPI_NBR, COUNT(*) as rx_count
          FROM `project.Claims.rx_claims`
          WHERE NDC_DRUG_NM = 'HUMIRA'
          AND PRESCRIBER_NPI_STATE_CD = 'CA'
          GROUP BY PRESCRIBER_NPI_NBR
          ORDER BY rx_count DESC
          LIMIT 10",
  "dataset_name": "humira_ca_top10",
  "description": "Top HUMIRA prescribers in California"
}

Output: Saved 10 rows to humira_ca_top10.csv

PRESCRIBER_NPI_NBR  rx_count
1234567890          245
0987654321          189
...

The top 10 HUMIRA prescribers in California account for 1,543
total prescriptions. The leading prescriber (NPI 1234567890)
wrote 245 prescriptions.

Would you like me to:
1. Join with provider biographical data to see their specialties?
2. Analyze prescription trends over time?
3. Compare with other states?
```

### Domain-Specific Evaluators

```python
class SQLEvaluator(BaseEvaluator):
    """Validate healthcare SQL queries"""

    @property
    def prompt_template(self) -> str:
        return """Evaluate this healthcare SQL query:

Query: {sql}
Context: {context}

Check for:
1. Correct table/column names
2. Appropriate JOINs for healthcare data
3. HIPAA compliance (no PII in results)
4. Performance (proper indexing)
5. Logic errors

Respond with JSON:
{{
  "score": <0-100>,
  "passed": <true/false>,
  "issues": [],
  "reasoning": "..."
}}"""
```

### Results

**88 comprehensive tests**, including:
- 16 real API tests with Anthropic Claude
- Tool integration tests
- Security validation tests
- End-to-end workflow tests

**Production metrics:**
- Handles complex multi-table joins
- Processes 100K+ row datasets
- Generates visualizations
- Explains insights in plain English

---

## Building Your Own Agent

### Step-by-Step Guide

**1. Define Your Domain**

Questions to answer:
- What tasks will the agent perform?
- What data sources does it need?
- What actions can it take?
- Who are the users?
- What's the security model?

**Examples:**
- **Financial analyst**: Query databases, run models, generate reports
- **DevOps engineer**: Deploy services, monitor logs, debug issues
- **Customer support**: Query CRM, update tickets, send emails
- **Content writer**: Research topics, generate drafts, edit content

**2. Design System Prompt**

Template:

```python
SYSTEM_PROMPT = """You are a [ROLE] with access to [CAPABILITIES].

**Your Environment:**
[Description of data, APIs, constraints]

**Available Tools:**
- Tool1: Description
- Tool2: Description
...

**Workflow:**
1. Understand [user's goal]
2. [Step-by-step process]
3. Present results clearly

**Guidelines:**
- [Domain-specific best practices]
- [Output format preferences]
- [Error handling approach]

Current date: {current_date}"""
```

**3. Implement Core Tools**

Start with essentials:

```python
# Essential tools for most agents
tools = [
    BashTool(workspace_dir),      # Execute commands
    ReadTool(workspace_dir),       # Read files
    WriteTool(workspace_dir),      # Create files
    EditTool(workspace_dir),       # Modify files
]

# Add domain-specific tools
if domain == "data_analysis":
    tools.append(SQLTool(db_connection))
    tools.append(PythonTool(workspace_dir))

if domain == "devops":
    tools.append(KubernetesTool(kube_config))
    tools.append(LogsTool(log_provider))

if domain == "customer_support":
    tools.append(CRMTool(crm_api_key))
    tools.append(EmailTool(smtp_config))
```

**4. Add Security Hooks**

```python
# Path validation for file tools
path_hook = create_path_validation_prehook(workspace_dir)
agent.tools.set_prehook("Read", path_hook)
agent.tools.set_prehook("Write", path_hook)
agent.tools.set_prehook("Edit", path_hook)

# Resource limits for execution
resource_hook = create_resource_limit_hook(
    max_cpu_seconds=60,
    max_memory_mb=512
)
agent.tools.set_prehook("Bash", resource_hook)
```

**5. Implement Agentic Loop**

```python
class MyAgent(AutonomousAgent):
    def __init__(self, session_id, workspace_dir):
        super().__init__(
            session_id=session_id,
            workspace_dir=workspace_dir,
            system_prompt=SYSTEM_PROMPT
        )

        # Register tools
        self.tools.register(BashTool(workspace_dir))
        self.tools.register(ReadTool(workspace_dir))
        # ... register all tools

        # Add security hooks
        path_hook = create_path_validation_prehook(workspace_dir)
        self.tools.set_prehook("Read", path_hook)
        self.tools.set_prehook("Write", path_hook)
```

**6. Add Observability**

```python
# Debug logging
from debug import log, with_session

# Wrap agent
agent.run = with_session(session_id)(agent.run)

# LLM tracing (optional)
if os.getenv("LANGFUSE_ENABLED") == "1":
    from observability import langfuse_client
    langfuse_client.setup()
    agent.run = langfuse_client.trace_run(
        session_id,
        workspace_dir
    )(agent.run)
```

**7. Write Tests**

```python
# test_agent.py
import pytest
from my_agent import MyAgent

@pytest.mark.asyncio
async def test_basic_task():
    """Test agent can complete basic task"""
    agent = MyAgent(
        session_id="test",
        workspace_dir="/tmp/test"
    )

    messages = []
    async for msg in agent.run("Create hello.txt with 'Hello World'"):
        messages.append(msg)

    # Verify file created
    assert Path("/tmp/test/hello.txt").exists()
    assert Path("/tmp/test/hello.txt").read_text() == "Hello World"

@pytest.mark.asyncio
async def test_security():
    """Test path validation prevents escape"""
    agent = MyAgent(session_id="test", workspace_dir="/tmp/test")

    with pytest.raises(SecurityError):
        async for msg in agent.run("Read /etc/passwd"):
            pass
```

**8. Deploy**

Choose deployment strategy (see Deployment Strategies section):
- Local CLI for development
- Serverless (Modal/Lambda) for production
- Kubernetes for enterprise

---


## Best Practices

### Design

1. **Start simple, iterate**
   - Begin with 3-5 core tools
   - Add complexity as needed
   - Don't over-engineer upfront

2. **System prompt is critical**
   - Be specific about capabilities
   - Provide examples
   - Set clear expectations

3. **Tool granularity**
   - One tool = one capability
   - Compose complex actions from simple tools
   - Avoid monolithic tools

4. **Error messages matter**
   - Clear, actionable errors
   - Suggest fixes
   - Include context

### Security

1. **Validate everything**
   - Path validation for all file ops
   - Input schema validation
   - Output sanitization

2. **Principle of least privilege**
   - Only necessary permissions
   - Workspace isolation
   - Network restrictions

3. **Resource limits**
   - CPU/memory caps
   - Execution timeouts
   - Rate limiting

4. **Audit trail**
   - Log all tool executions
   - Track data access
   - Compliance requirements

### Performance

1. **Async all the way**
   - Non-blocking I/O
   - Concurrent tool execution (when safe)
   - Streaming responses

2. **Temperature=0 for consistency**
   - Deterministic behavior
   - Easier testing
   - Better debugging

3. **Smart caching**
   - Cache LLM responses
   - Cache tool results (when safe)
   - Invalidate appropriately

4. **Optimize token usage**
   - Concise system prompts
   - Truncate large outputs
   - Smart context management

### Testing

1. **Unit test every tool**
   - Happy path
   - Error cases
   - Security validation

2. **Integration tests**
   - Tool combinations
   - Multi-turn conversations
   - Edge cases

3. **Real API tests**
   - Test with actual LLM
   - Verify streaming works
   - Check conversation history

4. **Evaluation suite**
   - Automated quality checks
   - Regression tests
   - Benchmark performance

### Operations

1. **Observability first**
   - Debug logging for development
   - Structured logging for production
   - LLM tracing for costs

2. **Graceful degradation**
   - Handle API failures
   - Retry with backoff
   - Fallback strategies

3. **Cost monitoring**
   - Track token usage
   - Set budgets
   - Optimize prompts

4. **Continuous improvement**
   - Analyze failures
   - Update system prompts
   - Add missing tools

---

## Implementation Standards for agent_v5

### Code Quality Requirements

**agent_v5 framework follows strict implementation standards:**

1. **Tool Implementation**
   - All tools inherit from `BaseTool` abstract class
   - Required methods: `name`, `schema`, `execute(input) -> Dict`
   - Prehook pattern for validation (`prehook()` method)
   - Return format: `{"content": str, "is_error": bool}`
   - Workspace-scoped (tools operate within `workspace_dir`)

2. **Testing Standards**
   - **2,651 lines of test code** across 111 test cases
   - Real API tests (not mocked) - tests use actual Anthropic API
   - Comprehensive coverage: unit tests, integration tests, e2e tests
   - All tests use `pytest.mark.asyncio` for async execution
   - Temporary workspace directories for isolation

3. **Agent Architecture**
   - `ResearchAgent` class with agentic loop in `agent.py`
   - Tool registry pattern for centralized management
   - Streaming responses via `AsyncGenerator[Dict, None]`
   - Temperature=0 for deterministic behavior
   - Debug logging via `debug.py` (enabled with `DEBUG=1`)

### Symlink Architecture

**mle-bench integration uses symlinks to eliminate duplication:**

- `mle-bench/agents/agent_v5_kaggle/` contains kaggle-specific code
- Shared resources use symlinks to canada-research root:
  - `agent_v5/` → `../../../agent_v5` (framework)
  - `debug.py` → `../../../debug.py` (logging)
  - `observability/` → `../../../observability` (tracing)
  - `security/` → `../../../security` (validation)

**Benefits:**
- Single source of truth - changes propagate automatically
- No code duplication (~400 lines eliminated)
- Maintains mle-bench as regular directory (not submodule)

**Updating mle-bench from upstream:**
```bash
git subtree pull --prefix=mle-bench https://github.com/openai/mle-bench.git main --squash
```

### Key Implementation Patterns

1. **Streaming Pattern**
   ```python
   async def run(self, user_message: str) -> AsyncGenerator[Dict, None]:
       while True:
           # Stream text deltas
           yield {"type": "text_delta", "text": chunk}

           # Execute tools
           yield {"type": "tool_execution", "tool_name": name, ...}

           # Signal completion
           yield {"type": "done"}
   ```

2. **Prehook Validation Pattern**
   ```python
   async def prehook(self, input: Dict) -> None:
       if self._custom_prehook:
           await self._custom_prehook(input)  # Validates/normalizes input
   ```

3. **Tool Registration Pattern**
   ```python
   def _register_core_tools(self):
       self.tools.register(BashTool(self.workspace_dir))
       self.tools.register(ReadTool(self.workspace_dir))
       # ... register all tools
   ```

**When building agents: Follow agent_v5 patterns for consistency and reliability.**

---

## Summary

### Key Takeaways

**Architecture:**
- Agent-Tool-Registry pattern is foundational
- Agentic loop enables multi-step reasoning
- Workspace isolation for security
- Prehooks for validation

**Tools:**
- BaseTool interface for consistency
- Registry for centralized management
- MCP proxy for external integrations
- Domain-specific tools for specialization

**Security:**
- Path validation prevents escapes
- Resource limits prevent abuse
- Sandbox execution (containers/VMs)
- Audit logging for compliance

**Observability:**
- Debug logging for development
- LLM tracing for production
- Structured logging for analysis
- Quality evaluations for improvement

**Deployment:**
- Local for development
- Serverless for production
- Containers for enterprise
- Choose based on requirements

### What You Can Build

With this framework, you can build agents for:

- 📊 **Data Analysis**: Query databases, analyze trends, create reports
- 🔧 **DevOps**: Deploy services, monitor systems, debug issues
- 📝 **Content Creation**: Research topics, write drafts, edit content
- 🎯 **Customer Support**: Query CRM, update tickets, send emails
- 🔬 **Research**: Literature review, data collection, hypothesis testing
- 💼 **Business Intelligence**: KPI tracking, forecasting, insights
- 🏥 **Healthcare**: Clinical research, population health, care coordination
- 💰 **Finance**: Portfolio analysis, risk assessment, compliance

### Next Steps

1. **Study the healthcare example** in this repo
2. **Run the tests** to understand behavior
3. **Build a simple agent** in your domain
4. **Add tools** specific to your use case
5. **Deploy locally** first, then serverless
6. **Monitor & iterate** based on usage

### Resources

**Code:**
- `agent_v5/` - Complete reference implementation
- `agent_v5/tests/` - 88 comprehensive tests
- `bigquery_tool.py` - Example MCP integration

**Documentation:**
- `agent_v5/README.md` - Implementation details
- `EVALS_USAGE.md` - Quality evaluation guide
- This file - Complete framework guide

**Further Reading:**
- Anthropic Tool Use API docs
- Model Context Protocol (MCP)
- LangChain agent patterns
- AutoGPT architecture

---

## Appendix: Reference Implementation

### Minimal Agent (50 lines)

```python
# minimal_agent.py
import os
import asyncio
from anthropic import Anthropic

class MinimalAgent:
    def __init__(self, tools):
        self.client = Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
        self.tools = tools
        self.history = []

    async def run(self, message):
        self.history.append({"role": "user", "content": message})

        while True:
            response = self.client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=4096,
                messages=self.history,
                tools=self.tools
            )

            if response.stop_reason == "end_turn":
                return response.content[0].text

            # Execute tools
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = self.execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result
                    })

            self.history.append({"role": "assistant", "content": response.content})
            self.history.append({"role": "user", "content": tool_results})

    def execute_tool(self, name, input):
        # Implement your tools here
        return f"Tool {name} executed"

# Usage:
agent = MinimalAgent(tools=[...])
result = asyncio.run(agent.run("Create hello.txt"))
print(result)
```

### Tool Template

```python
# my_tool.py
from typing import Dict
from agent_v5.tools.base import BaseTool

class MyTool(BaseTool):
    """[Brief description of what this tool does]"""

    @property
    def name(self) -> str:
        return "MyTool"

    @property
    def schema(self) -> Dict:
        return {
            "name": "MyTool",
            "description": "Detailed description for LLM",
            "input_schema": {
                "type": "object",
                "properties": {
                    "param1": {
                        "type": "string",
                        "description": "What this parameter does"
                    },
                    "param2": {
                        "type": "number",
                        "description": "What this parameter does"
                    }
                },
                "required": ["param1"]
            }
        }

    async def execute(self, input: Dict) -> Dict:
        """Execute the tool"""
        try:
            # 1. Extract parameters
            param1 = input["param1"]
            param2 = input.get("param2", default_value)

            # 2. Perform operation
            result = self._do_work(param1, param2)

            # 3. Return success
            return {
                "content": str(result),
                "is_error": False,
                "debug_summary": f"Processed {param1}"  # For logging
            }
        except Exception as e:
            # 4. Return error
            return {
                "content": f"Error: {str(e)}",
                "is_error": True
            }

    def _do_work(self, param1, param2):
        """Internal implementation"""
        # Your logic here
        return result
```

---

**End of Guide**

*Last updated: 2025-10-08*
*Framework Version: 1.0.0*

**Built with this framework:**
- Healthcare Research Agent (this repo)
- 88 comprehensive tests
- Production-ready deployment on Modal
- Real-world usage analyzing 100K+ row datasets

**Ready to build your own autonomous agent? Start with `agent_v5/` as reference.**
