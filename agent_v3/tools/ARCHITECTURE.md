# Tool Hint System Architecture

## Overview

The agent uses a **tool-owned hint system** that eliminates hardcoded tool names from the orchestrator. Each tool is responsible for providing its own hints to guide the LLM after execution.

## Core Components

### 1. Tool Categories (`tools/categories.py`)

All tools MUST declare their category using the `ToolCategory` enum:

```python
class ToolCategory(Enum):
    SQL_GENERATION = "sql_generation"      # Generates SQL queries
    SQL_EXECUTION = "sql_execution"        # Executes SQL queries
    COMMUNICATION = "communication"         # User interaction
    COMPLETION = "completion"               # Session finalization
    OTHER = "other"                         # Custom tools
```

### 2. Tool Base Class (`tools/base.py`)

The `Tool` base class now includes:

```python
class Tool(ABC):
    def __init__(self, name: str, description: str, category: ToolCategory):
        self.name = name
        self.description = description
        self.category = category  # REQUIRED

    def get_success_hint(self, context: Context) -> Optional[str]:
        """Override to provide hint after successful execution"""
        return None

    def get_error_hint(self, context: Context) -> Optional[str]:
        """Override to provide hint after error (default provided)"""
        from agent_v3.prompts import hints
        return hints.get_error_handling_hint()
```

### 3. Hint Prompts (`prompts/hints.py`)

All hint text is centralized in `prompts/hints.py`:

- `get_force_tool_selection_message(tools)` - Force LLM to select tool
- `get_sql_generated_hint()` - After SQL generation
- `get_query_executed_hint(num_datasets)` - After SQL execution
- `get_error_handling_hint()` - After errors

### 4. Orchestrator (`orchestrator.py`)

The orchestrator is now **tool-agnostic**:

```python
def _add_contextual_hints(self):
    last_execution = self.context.get_last_tool_execution()
    if not last_execution:
        return

    tool = self.tools[last_execution.tool_name]

    # Tool provides its own hint
    if last_execution.error:
        hint = tool.get_error_hint(self.context)
    else:
        hint = tool.get_success_hint(self.context)

    if hint:
        self.context.add_system_hint(hint)
```

## Creating New Tools

### Step 1: Import Required Components

```python
from agent_v3.tools.base import Tool, ToolResult
from agent_v3.tools.categories import ToolCategory
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from agent_v3.context import Context
```

### Step 2: Define Tool with Category

```python
class MyCustomTool(Tool):
    def __init__(self):
        super().__init__(
            name="my_custom_tool",
            description="Does something amazing",
            category=ToolCategory.OTHER  # Choose appropriate category
        )
```

### Step 3: Implement Hint Methods (Optional)

```python
    def get_success_hint(self, context: 'Context') -> Optional[str]:
        """Provide custom hint after success"""
        from agent_v3.prompts import hints
        # Return custom hint or use existing ones
        return "Custom hint based on tool execution"

    def get_error_hint(self, context: 'Context') -> Optional[str]:
        """Override only if custom error handling needed"""
        # Default error hint is already provided by base class
        return super().get_error_hint(context)
```

### Step 4: Register Tool

Add to `tools/__init__.py`:

```python
from .my_custom_tool import MyCustomTool

def get_all_tools():
    return {
        # ... existing tools ...
        "my_custom_tool": MyCustomTool(),
    }
```

## Benefits

### ✅ No Hardcoded Tool Names
- Orchestrator doesn't know about specific tools
- No `if tool_name == "text_to_sql_rx"` checks

### ✅ Automatic Hint System
- Tools own their hint logic
- Adding/removing tools doesn't break orchestrator

### ✅ Context-Aware Hints
- Hints can access context (e.g., number of datasets)
- Dynamic hint generation based on execution state

### ✅ Type Safety
- Categories are enforced via enum
- Required category parameter prevents missing categorization

### ✅ Easy Testing
- Mock tools and verify hints independently
- No orchestrator dependency for hint testing

## Example: SQL Generation Tool

```python
class TextToSQLRx(Tool):
    def __init__(self):
        super().__init__(
            name="text_to_sql_rx",
            description="Generate SQL for rx_claims",
            category=ToolCategory.SQL_GENERATION
        )

    def get_success_hint(self, context: 'Context') -> Optional[str]:
        from agent_v3.prompts import hints
        return hints.get_sql_generated_hint()

    # Error hint inherited from base class
```

## Example: SQL Execution Tool

```python
class BigQuerySQLQuery(Tool):
    def __init__(self):
        super().__init__(
            name="bigquery_sql_query",
            description="Execute SQL on BigQuery",
            category=ToolCategory.SQL_EXECUTION
        )

    def get_success_hint(self, context: 'Context') -> Optional[str]:
        from agent_v3.prompts import hints
        # Context-aware hint based on number of datasets
        datasets = context.get_all_datasets()
        return hints.get_query_executed_hint(len(datasets))
```

## Migration Checklist

When adding a new tool:

- [ ] Import `ToolCategory` from `agent_v3.tools.categories`
- [ ] Pass `category` parameter to `super().__init__()`
- [ ] Implement `get_success_hint()` if custom hint needed
- [ ] Implement `get_error_hint()` only if custom error hint needed
- [ ] Add hint text to `prompts/hints.py` if new pattern
- [ ] Register tool in `tools/__init__.py`
- [ ] Test tool hints independently

## Common Patterns

### No Hint Needed
```python
def get_success_hint(self, context: 'Context') -> Optional[str]:
    return None  # Tool doesn't need hints
```

### Simple Static Hint
```python
def get_success_hint(self, context: 'Context') -> Optional[str]:
    from agent_v3.prompts import hints
    return hints.get_some_hint()
```

### Context-Aware Hint
```python
def get_success_hint(self, context: 'Context') -> Optional[str]:
    from agent_v3.prompts import hints
    data = context.get_all_datasets()
    if len(data) > 5:
        return hints.get_too_much_data_hint()
    return hints.get_normal_hint(len(data))
```

### Conditional Hint
```python
def get_success_hint(self, context: 'Context') -> Optional[str]:
    from agent_v3.prompts import hints
    last_result = context.get_last_tool_result()
    if "complex" in last_result.get("analysis_type", ""):
        return hints.get_complex_analysis_hint()
    return None
```
