# Sandbox Code Execution Architecture

## Overview

Three-tool system for advanced data analysis using Modal sandboxes with Polars.

**Core Principle**: Simple, composable tools + LLM orchestration through recursion.

---

## Tool Specifications

### Tool 1: `sandbox_exec`

**Purpose**: Execute commands in isolated Modal sandbox

#### Call Format
```json
{
    "tool": "sandbox_exec",
    "parameters": {
        "command": ["python", "/tmp/analysis.py"],
        "timeout": 60
    },
    "reasoning_trace": "Running clustering analysis"
}
```

#### Response Format
```json
{
    "exit_code": 0,
    "stdout": "Created 3 clusters\nSilhouette score: 0.72\n",
    "stderr": "",
    "stdout_truncated": false,
    "stderr_truncated": false,
    "output_files": ["clusters.csv", "plot.png"],
    "total_output_files": 2,
    "execution_time": 2.3
}
```

#### Behavior
1. Check `context.sandbox` for existing sandbox
2. **If missing**: Create new sandbox with Modal
3. **If first creation**: Mount all CSVs from `context.csv_paths` to `/tmp/data/`
4. Execute command via `sandbox.exec()`
5. Capture stdout/stderr (truncate if > 10KB)
6. **After execution**: Retrieve files from `/tmp/output/`
7. Return execution results + file list

#### Sandbox Configuration
```python
modal.Sandbox.create(
    image=modal.Image.debian_slim(python_version="3.11")
        .pip_install(
            "polars",
            "numpy",
            "matplotlib",
            "seaborn",
            "scikit-learn"
        ),
    timeout=timeout,
    block_network=True,
    app=app
)
```

---

### Tool 2: `sandbox_write_file`

**Purpose**: Create or overwrite files in sandbox

#### Call Format
```json
{
    "tool": "sandbox_write_file",
    "parameters": {
        "file_path": "/tmp/analysis.py",
        "content": "import polars as pl\n..."
    },
    "reasoning_trace": "Creating analysis script"
}
```

#### Response Format
```json
{
    "success": true,
    "file_path": "/tmp/analysis.py",
    "bytes_written": 1524
}
```

**Error (invalid path)**:
```json
{
    "success": false,
    "error": "Invalid path: must be /tmp/* or /workspace/*",
    "file_path": "/home/bad.py"
}
```

#### Behavior
1. Validate file_path starts with `/tmp/` or `/workspace/`
2. Validate content size < 5MB
3. Ensure sandbox exists (create if needed)
4. Write content using `sandbox.open(file_path, "w")`
5. Return success + bytes written

---

### Tool 3: `sandbox_edit_file`

**Purpose**: Modify existing files via exact string replacement

#### Call Format
```json
{
    "tool": "sandbox_edit_file",
    "parameters": {
        "file_path": "/tmp/analysis.py",
        "old_string": "n_clusters=3",
        "new_string": "n_clusters=5, random_state=42"
    },
    "reasoning_trace": "Increasing clusters and adding seed"
}
```

#### Response Format
```json
{
    "success": true,
    "file_path": "/tmp/analysis.py"
}
```

**Error (not unique)**:
```json
{
    "success": false,
    "error": "old_string found 3 times - not unique. Include more context.",
    "file_path": "/tmp/analysis.py"
}
```

#### Behavior
1. Read file content via `sandbox.exec(["cat", file_path])`
2. Count occurrences of `old_string`
   - 0 matches → Error: "old_string not found"
   - >1 matches → Error: "not unique (found N matches)"
3. Replace: `content.replace(old_string, new_string, 1)`
4. Write back via `sandbox.open(file_path, "w")`
5. Return success

---

## Sandbox Lifecycle

### Creation (Lazy Initialization)
- **When**: First tool call in session
- **Storage**: `context.sandbox` (Modal Sandbox instance)
- **CSV Mounting**: Automatic on creation

### Persistence
- Lives for entire session
- All tools share same sandbox
- Files persist across tool calls
- State preserved between executions

### Cleanup
- **When**: Context cleanup (session end)
- **How**: `context.sandbox.terminate()` in context destructor
- **Fallback**: Modal auto-terminates after timeout

---

## CSV Mounting Strategy

**When**: On first sandbox creation
**Where**: `/tmp/data/{dataset_name}.csv`

### Implementation
```python
def mount_csvs_to_sandbox(context):
    """Copy all session CSVs to sandbox /tmp/data/"""
    sandbox = context.sandbox

    # Create directory
    sandbox.exec("mkdir", "-p", "/tmp/data").wait()

    # Copy each CSV
    for dataset_name, local_csv_path in context.csv_paths.items():
        # Read local file
        with open(local_csv_path, 'rb') as f:
            csv_data = f.read()

        # Sanitize filename
        safe_name = dataset_name.replace('/', '_').replace(' ', '_')
        remote_path = f"/tmp/data/{safe_name}.csv"

        # Write to sandbox
        with sandbox.open(remote_path, 'wb') as sf:
            sf.write(csv_data)

    context.sandbox_mounted = True
```

---

## Output File Retrieval

**When**: After every `sandbox_exec` execution
**Where**: `/tmp/output/` in sandbox → `output/session_{id}/` locally

### Implementation
```python
def retrieve_output_files(sandbox, context):
    """Copy sandbox output files to local session directory"""

    # List files in /tmp/output/
    result = sandbox.exec("find", "/tmp/output", "-type", "f")
    result.wait()

    if result.returncode != 0:
        return []

    file_paths = result.stdout.read().strip().split('\n')
    output_files = []

    # Process each file (max 20)
    for remote_path in file_paths[:20]:
        if not remote_path or remote_path == '/tmp/output':
            continue

        filename = remote_path.split('/')[-1]

        # Read from sandbox
        with sandbox.open(remote_path, 'rb') as sf:
            content = sf.read()

        # Save locally
        local_path = f"output/session_{context.session_id}/{filename}"
        with open(local_path, 'wb') as lf:
            lf.write(content)

        # Handle visualizations
        if filename.endswith(('.png', '.jpg', '.svg', '.jpeg')):
            io_handler = getattr(context, 'io_handler', None)
            if io_handler and hasattr(io_handler, 'send_visualization'):
                io_handler.send_visualization(local_path)

        output_files.append(filename)

    return output_files
```

### Output Types Handled

1. **CSV** - Auto-save locally, don't parse
2. **Images (PNG/JPG/SVG)** - Auto-save + send to WebSocket
3. **JSON** - Auto-save, LLM reads if needed
4. **Text/Logs** - Auto-save locally
5. **Binary/Models** - List in response, stay in sandbox

---

## File Access Pattern

LLM reads sandbox files using `sandbox_exec` with Unix commands:

```json
// Preview CSV
{"tool": "sandbox_exec", "parameters": {"command": ["head", "-20", "/tmp/output/results.csv"]}}

// Read JSON
{"tool": "sandbox_exec", "parameters": {"command": ["cat", "/tmp/output/metrics.json"]}}

// Search in logs
{"tool": "sandbox_exec", "parameters": {"command": ["grep", "error", "/tmp/output/log.txt"]}}

// List output
{"tool": "sandbox_exec", "parameters": {"command": ["ls", "-lh", "/tmp/output"]}}

// Count rows
{"tool": "sandbox_exec", "parameters": {"command": ["wc", "-l", "/tmp/output/data.csv"]}}
```

**Why**: No dedicated read tool needed, Unix commands are battle-tested.

---

## Security Constraints

1. **Network isolation**: `block_network=True`
2. **Timeout**: 60s default, 300s max
3. **Path validation**: Only `/tmp/*` and `/workspace/*`
4. **Content size**: Max 5MB per file write
5. **Output limit**: Max 20 files retrieved per execution
6. **Stdout/stderr truncation**: 10KB limit with flag

---

## Context Extensions

Add to `context.py`:

```python
from typing import Optional
import modal

class Context:
    def __init__(self, session_id: str, io_handler=None):
        # ... existing fields ...
        self.sandbox: Optional[modal.Sandbox] = None
        self.sandbox_mounted: bool = False

    def cleanup(self):
        """Cleanup resources on session end"""
        if self.sandbox:
            try:
                self.sandbox.terminate()
            except:
                pass
```

---

## Tool Categories

Add to `tools/categories.py`:

```python
class ToolCategory(Enum):
    # ... existing ...
    CODE_EXECUTION = "code_execution"
    FILE_MANAGEMENT = "file_management"
```

---

## System Prompt Integration

Add to `prompts/system_prompt.py`:

```markdown
## ADVANCED ANALYSIS (Sandboxed Code Execution)

For analysis beyond SQL (clustering, ML, statistical analysis, visualization):

**TOOLS:**
- `sandbox_write_file`: Create Python scripts in sandbox
- `sandbox_edit_file`: Modify scripts via exact string replacement
- `sandbox_exec`: Execute commands in isolated sandbox

**WORKFLOW:**
1. Write script: `sandbox_write_file`
2. Execute: `sandbox_exec`
3. If errors: Read output, edit script, re-run

**DATA ACCESS:**
- Datasets at: `/tmp/data/{dataset_name}.csv`
- MUST use Polars: `pl.read_csv('/tmp/data/{name}.csv')`
- Save outputs: `/tmp/output/result.csv`
- Save plots: `/tmp/output/plot.png`

**POLARS EXAMPLE:**
```python
import polars as pl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans

# Load
df = pl.read_csv('/tmp/data/prescribers.csv')

# Cluster
X = df.select(['volume', 'count']).to_numpy()
kmeans = KMeans(n_clusters=3, random_state=42).fit(X)
df = df.with_columns(pl.Series('cluster', kmeans.labels_))

# Save
df.write_csv('/tmp/output/clustered.csv')

# Plot
plt.figure(figsize=(10,6))
plt.scatter(X[:,0], X[:,1], c=kmeans.labels_, cmap='viridis')
plt.xlabel('Volume')
plt.ylabel('Count')
plt.title('Prescriber Clusters')
plt.savefig('/tmp/output/plot.png', dpi=150, bbox_inches='tight')
plt.close()

print(f"Created {len(set(kmeans.labels_))} clusters")
```

**CONSTRAINTS:**
- Timeout: 60s (adjustable to 300s max)
- No network access
- NO PANDAS - Use Polars only
- Files in /tmp/ or /workspace/ only
- Output files in /tmp/output/
```

---

## Hints

### `sandbox_exec`
- **Success + files**: "Code executed successfully. {N} output files created. Consider using 'complete' to present results."
- **Success + no files**: "Code executed but no outputs in /tmp/output/. Verify script saves results."
- **Exit ≠ 0**: "Execution failed. Review stderr and use sandbox_edit_file to fix errors."

### `sandbox_write_file`
- **Success**: "File written successfully. Use sandbox_exec to run it."
- **Path error**: "Invalid path. Use /tmp/ or /workspace/ only."

### `sandbox_edit_file`
- **Success**: "File edited successfully. Re-run with sandbox_exec."
- **Not unique**: "Edit failed - old_string not unique. Include more surrounding context."
- **Not found**: "Edit failed - old_string not found. Read file first with sandbox_exec."

---

## Error Recovery Patterns

### Pattern 1: Execution Error
1. `sandbox_exec` returns exit_code ≠ 0
2. LLM reads stderr
3. LLM identifies bug
4. `sandbox_edit_file` to fix
5. Re-run `sandbox_exec`

### Pattern 2: Edit Not Unique
1. `sandbox_edit_file` fails (multiple matches)
2. LLM reads file: `sandbox_exec(["cat", "/tmp/script.py"])`
3. LLM selects unique substring with context
4. Retry `sandbox_edit_file`

### Pattern 3: Missing Output
1. `sandbox_exec` succeeds but no output_files
2. LLM checks: `sandbox_exec(["ls", "-la", "/tmp/output"])`
3. Realizes script doesn't save to /tmp/output/
4. `sandbox_edit_file` to fix save paths
5. Re-run

---

## Testing Checklist

- [ ] Simple Python execution (hello world)
- [ ] CSV loading from /tmp/data/
- [ ] Polars analysis with results
- [ ] sklearn clustering + visualization
- [ ] Error recovery (buggy code → fix → success)
- [ ] Edit uniqueness error → read → fix → success
- [ ] Multiple files in /tmp/output/
- [ ] Large stdout truncation
- [ ] Path validation (reject /home/)
- [ ] Network blocking (requests fails)
- [ ] Timeout enforcement
- [ ] Context cleanup (sandbox termination)

---

## Implementation Files

1. `tools/code_execution/sandbox_exec/main.py`
2. `tools/code_execution/sandbox_write_file/main.py`
3. `tools/code_execution/sandbox_edit_file/main.py`
4. `tools/code_execution/prompts.py` (shared hints)
5. `tools/categories.py` (add categories)
6. `context.py` (add sandbox fields)
7. `prompts/system_prompt.py` (add tools + examples)

---

## Key Design Decisions

✅ **Persistent sandbox per session** - Efficient, stateful
✅ **Auto CSV mounting** - Predictable, simple
✅ **Exact string replacement** - Battle-tested, no bloat
✅ **Auto output retrieval** - Better UX, automatic
✅ **Unix commands for file access** - No dedicated read tool
✅ **Truncation with flags** - Prevents bloat, clear indicators
✅ **Polars-only** - Fast, modern, explicit

---

## NOT INCLUDED (Bloat Prevention)

❌ Line-based editing
❌ Regex patterns in edits
❌ Multiple edits per call
❌ Auto-parsing of outputs
❌ Dedicated file read tool
❌ Append mode
❌ Binary diff tools
❌ Fuzzy matching
❌ Volumes/mounts (simple file I/O only)
