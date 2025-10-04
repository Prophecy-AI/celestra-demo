# TUI Usage

## Launch

```bash
python -m agent_v3              # Default: launches TUI
python -m agent_v3 tui          # Explicit TUI launch
```

## Features

### Main Screen (Tool List)

**Keybindings:**
- `↑/↓` - Navigate tools
- `e` - Edit selected tool's prompt (opens YAML editor)
- `n` - Create new SQL tool
- `r` - Refresh tool list
- `q` - Quit

**Columns:**
- **Tool Name** - Identifier for the tool
- **Type** - SQL or Other
- **Status** - ✅ valid, ⚠️ has issues
- **Prompt File** - Yes/No if YAML prompt exists

### Prompt Editor (`e`)

Edit YAML prompts directly in the TUI.

**Keybindings:**
- `ctrl+s` - Save changes
- `escape` - Cancel (discard changes)

Changes take effect immediately - no restart needed.

### New Tool Creator (`n`)

Create a new SQL tool from template.

**Fields:**
- Tool name (e.g., `text_to_sql_pharmacy`)
- Class name (e.g., `TextToSQLPharmacy`)
- Description
- Table name (full BigQuery path)
- Columns (JSON array)

**Columns JSON format:**
```json
[
  {"name": "COLUMN_NAME", "type": "STRING", "description": "What it is"},
  {"name": "DATE_FIELD", "type": "DATE", "description": "When it happened"}
]
```

**Keybindings:**
- `ctrl+g` or click "Generate" - Create tool
- `escape` or click "Cancel" - Abort

**Generated files:**
- `agent_v3/tools/[tool_name].py` - Python tool class
- `agent_v3/prompts/tools/[tool_name].yaml` - YAML prompt

## Running Agent Queries

```bash
python -m agent_v3 main --query "Your query here"
python -m agent_v3 main --debug --query "Your query here"
```

## Example Workflow

1. Launch TUI: `python -m agent_v3`
2. Press `e` to edit a prompt
3. Modify YAML, press `ctrl+s` to save
4. Press `escape` to return
5. Press `n` to create new tool
6. Fill form, press `ctrl+g` to generate
7. Press `r` to refresh and see new tool
8. Press `q` to quit
9. Test: `python -m agent_v3 main --query "test"`

## Single File Implementation

The entire TUI is in `agent_v3/tui.py` - 200 lines, no dependencies beyond Textual.

Features:
- ✅ View all tools
- ✅ Edit prompts (YAML)
- ✅ Create new SQL tools
- ✅ Keyboard-driven
- ✅ No bloat
