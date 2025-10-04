"""
Minimal TUI for tool and prompt management

Usage: python -m agent_v3.tui
"""
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, DataTable, TextArea, Static, Input, Button
from textual.containers import Container, Horizontal, Vertical
from textual.screen import Screen
from textual.binding import Binding
from pathlib import Path
from agent_v3.tools import ToolRegistry, ToolGenerator
from agent_v3.prompts.loader import PromptLoader


class PromptEditor(Screen):
    """Edit a prompt YAML file"""
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+s", "save", "Save"),
    ]

    def __init__(self, prompt_name: str, prompt_path: Path):
        super().__init__()
        self.prompt_name = prompt_name
        self.prompt_path = prompt_path
        self.original_content = prompt_path.read_text()

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(f"Editing: {self.prompt_name}", classes="title")
        yield TextArea(self.original_content, id="editor")
        yield Footer()

    def action_save(self) -> None:
        editor = self.query_one("#editor", TextArea)
        self.prompt_path.write_text(editor.text)
        self.app.pop_screen()
        self.app.notify(f"✅ Saved {self.prompt_name}")

    def action_cancel(self) -> None:
        self.app.pop_screen()


class NewToolScreen(Screen):
    """Create a new SQL tool"""
    BINDINGS = [
        Binding("escape", "cancel", "Cancel"),
        Binding("ctrl+g", "generate", "Generate"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static("Create New SQL Tool", classes="title")
        yield Vertical(
            Input(placeholder="Tool name (e.g., text_to_sql_pharmacy)", id="tool_name"),
            Input(placeholder="Class name (e.g., TextToSQLPharmacy)", id="class_name"),
            Input(placeholder="Description", id="description"),
            Input(placeholder="Table name (full BigQuery path)", id="table_name"),
            TextArea("", id="columns", classes="columns-area"),
            Static("Columns (JSON array): [{\"name\": \"...\", \"type\": \"...\", \"description\": \"...\"}]"),
            Horizontal(
                Button("Generate", variant="success", id="gen_btn"),
                Button("Cancel", variant="default", id="cancel_btn"),
            ),
        )
        yield Footer()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel_btn":
            self.app.pop_screen()
        elif event.button.id == "gen_btn":
            self.action_generate()

    def action_generate(self) -> None:
        import json

        tool_name = self.query_one("#tool_name", Input).value
        class_name = self.query_one("#class_name", Input).value
        description = self.query_one("#description", Input).value
        table_name = self.query_one("#table_name", Input).value
        columns_text = self.query_one("#columns", TextArea).text

        if not all([tool_name, class_name, description, table_name]):
            self.app.notify("⚠️ Fill all fields", severity="error")
            return

        try:
            columns = json.loads(columns_text) if columns_text.strip() else []
        except json.JSONDecodeError:
            self.app.notify("⚠️ Invalid JSON for columns", severity="error")
            return

        config = {
            "tool_name": tool_name,
            "class_name": class_name,
            "description": description,
            "table_name": table_name,
            "key_columns": columns,
        }

        gen = ToolGenerator()
        py_path, yaml_path, error = gen.create_tool("sql", config)

        if error:
            self.app.notify(f"❌ {error}", severity="error")
        else:
            self.app.notify(f"✅ Created {tool_name}")
            self.app.pop_screen()

    def action_cancel(self) -> None:
        self.app.pop_screen()


class ToolManagerApp(App):
    """Minimal tool and prompt manager"""
    CSS = """
    .title {
        background: $primary;
        color: $text;
        padding: 1;
        text-align: center;
    }
    .columns-area {
        height: 10;
    }
    """

    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("e", "edit_prompt", "Edit Prompt"),
        Binding("n", "new_tool", "New Tool"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id="tools_table")
        yield Footer()

    def on_mount(self) -> None:
        self.load_tools()

    def load_tools(self) -> None:
        table = self.query_one("#tools_table", DataTable)
        table.clear(columns=True)
        table.add_columns("Tool Name", "Type", "Status", "Prompt File")

        tools = ToolRegistry.get_all_tools()
        loader = PromptLoader()

        for name, tool in tools.items():
            tool_type = "SQL" if name.startswith("text_to_sql") else "Other"

            # Check if prompt exists
            prompt_file = loader.tools_dir / f"{name}.yaml"
            status = "✅" if ToolRegistry.validate_tool(tool) is None else "⚠️"
            has_prompt = "Yes" if prompt_file.exists() else "No"

            table.add_row(name, tool_type, status, has_prompt, key=name)

    def action_edit_prompt(self) -> None:
        table = self.query_one("#tools_table", DataTable)
        if table.cursor_row is None:
            self.notify("⚠️ Select a tool first", severity="warning")
            return

        row_key = table.get_row_key_at(table.cursor_row)
        tool_name = str(row_key)

        loader = PromptLoader()
        prompt_path = loader.tools_dir / f"{tool_name}.yaml"

        if not prompt_path.exists():
            self.notify(f"⚠️ No prompt file for {tool_name}", severity="warning")
            return

        self.push_screen(PromptEditor(tool_name, prompt_path))

    def action_new_tool(self) -> None:
        self.push_screen(NewToolScreen())

    def action_refresh(self) -> None:
        self.load_tools()
        self.notify("♻️ Refreshed")


def main():
    app = ToolManagerApp()
    app.run()


if __name__ == "__main__":
    main()
