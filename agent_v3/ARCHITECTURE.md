# Agent V3 Architecture

## Overview

Agent V3 uses a **modular, template-based architecture** with externalized prompts and dynamic tool generation.

## Core Components

### 1. Prompt Management (`prompts/`)

**PromptLoader** - Loads and renders prompts from YAML files
- Location: `prompts/loader.py`
- Features:
  - YAML-based prompt storage
  - Jinja2 template rendering
  - Variable injection (current_date, table_name, etc.)
  - Validation and metadata extraction

**Prompt Files:**
- `prompts/system/main_orchestrator.yaml` - Main orchestrator system prompt
- `prompts/tools/*.yaml` - Tool-specific prompts (4 SQL tools)

**Usage:**
```python
from agent_v3.prompts.loader import PromptLoader

loader = PromptLoader()
prompt = loader.load_prompt('text_to_sql_rx', variables={
    'current_date': '2024-10-04',
    'table_name': '`project.dataset.table`'
})
```

### 2. Tool Template System (`tools/templates/`)

**Base Template** - Abstract base class for all tool types
- Location: `tools/templates/base_template.py`
- Methods:
  - `generate_tool_code()` - Generate Python code
  - `generate_prompt()` - Generate YAML prompt
  - `validate_config()` - Validate configuration
  - `get_config_schema()` - Get expected schema

**SQL Tool Template** - Template for SQL conversion tools
- Location: `tools/templates/sql_tool_template.py`
- Generates:
  - Python tool class with LLM integration
  - YAML prompt with schema and examples
  - Built-in validation and error handling

**Extensible:**
Add new template types by:
1. Subclass `ToolTemplate`
2. Implement abstract methods
3. Register in `ToolGenerator`

### 3. Tool Generator (`tools/generator.py`)

**ToolGenerator** - Creates new tools from templates
- Features:
  - Validate configuration
  - Preview generated code (dry-run)
  - Create tool files (Python + YAML)
  - Delete tools

**Usage:**
```python
from agent_v3.tools import ToolGenerator

gen = ToolGenerator()

# List available templates
print(gen.list_templates())  # ['sql']

# Get schema for a template
schema = gen.get_template_schema('sql')

# Generate tool (preview mode)
code, yaml, error = gen.preview_tool('sql', config)

# Create tool files
python_path, yaml_path, error = gen.create_tool('sql', config)
```

### 4. Tool Registry (`tools/registry.py`)

**ToolRegistry** - Dynamic tool discovery and loading
- Features:
  - Automatic tool discovery
  - Tool validation
  - Retrieval by name

**Usage:**
```python
from agent_v3.tools import ToolRegistry

# Get all tools
tools = ToolRegistry.get_all_tools()

# Get specific tool
tool = ToolRegistry.get_tool('text_to_sql_rx')

# Validate tool
error = ToolRegistry.validate_tool(tool)
```

## Workflow

### Adding a New SQL Tool

1. **Define Configuration:**
```python
config = {
    "tool_name": "text_to_sql_pharmacy",
    "class_name": "TextToSQLPharmacy",
    "description": "Generate SQL for pharmacy data",
    "table_name": "`project.dataset.pharmacy_claims`",
    "key_columns": [
        {"name": "PHARMACY_NPI", "type": "STRING", "description": "..."}
    ],
    "aggregation_rules": ["..."],
    # ... more config
}
```

2. **Generate Tool:**
```python
gen = ToolGenerator()
python_path, yaml_path, error = gen.create_tool('sql', config)
```

3. **Tool is Automatically Registered:**
The new tool will be discovered by ToolRegistry on next import.

### Editing Prompts

1. Edit YAML file directly:
```bash
vi agent_v3/prompts/tools/text_to_sql_rx.yaml
```

2. Changes take effect immediately (no restart needed)

3. Jinja2 variables:
   - Use `{{ variable_name }}` for substitution
   - Escape JSON with `{{ '{"key": "value"}' }}`

## Architecture Diagram

```
┌─────────────────────────────────────────────┐
│           RecursiveOrchestrator             │
│  (Main agent loop - tool selection)         │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│           ToolRegistry                      │
│  (Dynamic tool discovery & loading)         │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│           Individual Tools                  │
│  ┌──────────────────────────────────────┐  │
│  │  TextToSQLRx                         │  │
│  │  ├─ PromptLoader.load_prompt()       │  │
│  │  └─ LLM Client                       │  │
│  ├──────────────────────────────────────┤  │
│  │  BigQuerySQLQuery                    │  │
│  │  Complete, Communicate, etc.         │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│           PromptLoader                      │
│  (Loads YAML prompts + Jinja2 rendering)   │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│           YAML Prompt Files                 │
│  prompts/system/main_orchestrator.yaml      │
│  prompts/tools/text_to_sql_*.yaml          │
└─────────────────────────────────────────────┘

┌─────────────────────────────────────────────┐
│           ToolGenerator                     │
│  (Creates new tools from templates)         │
└─────────────────┬───────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────┐
│           Tool Templates                    │
│  templates/base_template.py (abstract)      │
│  templates/sql_tool_template.py             │
│  (Future: api_template, etc.)               │
└─────────────────────────────────────────────┘
```

## File Structure

```
agent_v3/
├── prompts/
│   ├── loader.py                 # PromptLoader class
│   ├── system/
│   │   └── main_orchestrator.yaml
│   └── tools/
│       ├── text_to_sql_rx.yaml
│       ├── text_to_sql_med.yaml
│       ├── text_to_sql_provider_payments.yaml
│       └── text_to_sql_providers_bio.yaml
├── tools/
│   ├── __init__.py               # Exports Registry + Generator
│   ├── registry.py               # ToolRegistry
│   ├── generator.py              # ToolGenerator
│   ├── templates/
│   │   ├── base_template.py      # Abstract base
│   │   └── sql_tool_template.py  # SQL tool generator
│   ├── base.py                   # Tool base class
│   ├── sql_generation.py         # SQL tools (refactored)
│   ├── sql_execution.py          # BigQuery execution
│   └── io_tools.py               # Communicate, Complete
├── orchestrator.py               # Main recursive loop
├── llm_client.py                 # LLM interaction
├── context.py                    # Conversation state
└── main.py                       # Entry point

test_tool_generation.py           # Test script
```

## Testing

**End-to-End Test:**
```bash
python -m agent_v3.main --debug --query "Find prescribers of HUMIRA in California"
```

**Tool Generation Test:**
```bash
python test_tool_generation.py
```

**Registry Test:**
```python
from agent_v3.tools import ToolRegistry
tools = ToolRegistry.get_all_tools()
print(f"Loaded {len(tools)} tools")
```

## Benefits

1. **Separation of Concerns**: Prompts are separate from code
2. **Easy Editing**: Edit prompts without touching Python
3. **Version Control**: YAML diffs are readable
4. **Extensibility**: Add new tool types via templates
5. **Validation**: Built-in schema validation
6. **Reusability**: Templates reduce code duplication
7. **Testing**: Preview mode for safe experimentation

## Future Enhancements

- Terminal UI for tool/prompt management
- Auto-discovery of generated tools in registry
- More template types (API, computation, etc.)
- Prompt versioning and A/B testing
- Tool marketplace/sharing
