"""
Textual TUI app for managing agent tools with Git-based staging workflow
"""
import subprocess
import os
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, VerticalScroll
from textual.widgets import (
    Header,
    Footer,
    Button,
    Label,
    Input,
    Select,
    TextArea,
    RichLog,
    TabbedContent,
    TabPane,
    Static,
)
from textual.screen import Screen, ModalScreen
from textual import work
from textual.binding import Binding
from textual.reactive import reactive


# ============================================================================
# Git utilities
# ============================================================================


def run_git(cmd):
    """Run git command and return output"""
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=os.getcwd())
        if result.returncode != 0:
            return None, result.stderr
        return result.stdout, None
    except Exception as e:
        return None, str(e)


def get_current_branch():
    """Get current git branch"""
    output, _ = run_git(['git', 'branch', '--show-current'])
    return output.strip() if output else None


def get_original_branch(staging_branch):
    """Get original branch from staging branch description"""
    output, _ = run_git(['git', 'config', f'branch.{staging_branch}.description'])
    return output.strip() if output else 'main'


def create_staging_branch(original_branch):
    """Create staging branch"""
    timestamp = datetime.now().strftime('%Y%m%d-%H%M')
    staging_branch = f'staging-{timestamp}'

    run_git(['git', 'checkout', '-b', staging_branch])
    run_git(['git', 'config', f'branch.{staging_branch}.description', original_branch])

    return staging_branch


def get_tools():
    """Get list of all tools"""
    tools_dir = Path("agent_v3/tools")
    tools = []
    for item in tools_dir.iterdir():
        if item.is_dir() and (item / "prompts.py").exists():
            tools.append(item.name)
    return sorted(tools)


def get_uncommitted_files():
    """Get list of uncommitted files"""
    output, _ = run_git(['git', 'status', '--porcelain'])
    if not output:
        return []

    files = []
    for line in output.strip().split('\n'):
        if line:
            # Parse git status format: "XY filename"
            status = line[:2]
            filename = line[3:]
            files.append(f"{status.strip()} {filename}")
    return files


def get_unmerged_commits(staging_branch, original_branch):
    """Get commits in staging that aren't in original branch"""
    output, _ = run_git(['git', 'log', f'{original_branch}..{staging_branch}', '--pretty=format:%h %s'])
    if not output:
        return []

    commits = []
    for line in output.strip().split('\n'):
        if line:
            commits.append(line)
    return commits


def read_file(filepath):
    """Read file content"""
    try:
        with open(filepath, 'r') as f:
            return f.read()
    except Exception as e:
        return f"Error reading file: {e}"


def write_file(filepath, content):
    """Write content to file"""
    try:
        with open(filepath, 'w') as f:
            f.write(content)
        return True, None
    except Exception as e:
        return False, str(e)


# ============================================================================
# Modal Screens
# ============================================================================


class CreateStagingModal(ModalScreen):
    """Modal to create staging environment"""

    def compose(self) -> ComposeResult:
        with Container(id="staging-modal"):
            yield Label("Not in staging mode", id="modal-title")
            yield Label(f"Current branch: {get_current_branch()}")
            yield Label("\nYou must create a staging environment to edit tools.")
            yield Horizontal(
                Button("Create Staging Environment", variant="primary", id="create"),
                Button("Cancel", variant="default", id="cancel"),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            original = get_current_branch()
            staging = create_staging_branch(original)
            self.app.current_branch = staging
            self.app.is_staging = True
            self.app.notify(f"Created staging branch: {staging}")
            self.dismiss(True)
        else:
            self.app.exit()


class AddToolModal(ModalScreen):
    """Modal to add new tool"""

    def compose(self) -> ComposeResult:
        with Container(id="add-tool-modal"):
            yield Label("Add New Tool", id="modal-title")
            yield Input(placeholder="text_to_sql_custom", id="tool-name")
            yield Horizontal(
                Button("Create", variant="primary", id="create"),
                Button("Cancel", variant="default", id="cancel"),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "create":
            tool_input = self.query_one("#tool-name", Input)
            tool_name = tool_input.value.strip()

            if not tool_name:
                self.app.notify("Tool name cannot be empty", severity="error")
                return

            self.dismiss(tool_name)
        else:
            self.dismiss(None)


class QuitConfirmModal(ModalScreen):
    """Modal to confirm quit with unsaved changes"""

    def __init__(self, uncommitted_files, unmerged_commits, original_branch):
        super().__init__()
        self.uncommitted_files = uncommitted_files
        self.unmerged_commits = unmerged_commits
        self.original_branch = original_branch

    def compose(self) -> ComposeResult:
        with Container(id="quit-modal"):
            yield Label("⚠️  Unsaved Changes Detected", id="modal-title")

            if self.uncommitted_files:
                yield Label("\n📝 Uncommitted files:", classes="section-label")
                for file in self.uncommitted_files:
                    yield Label(f"  • {file}", classes="file-item")

            if self.unmerged_commits:
                yield Label(f"\n🔀 Unmerged commits ({len(self.unmerged_commits)}):", classes="section-label")
                for commit in self.unmerged_commits[:5]:  # Show first 5
                    yield Label(f"  • {commit}", classes="commit-item")
                if len(self.unmerged_commits) > 5:
                    yield Label(f"  ... and {len(self.unmerged_commits) - 5} more", classes="commit-item")

            yield Label("\nWhat would you like to do?", classes="section-label")

            yield Horizontal(
                Button(f"Merge to {self.original_branch}", variant="primary", id="merge"),
                Button("Discard Changes", variant="error", id="discard"),
                Button("Cancel", variant="default", id="cancel"),
            )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "merge":
            self.dismiss("merge")
        elif event.button.id == "discard":
            self.dismiss("discard")
        else:
            self.dismiss("cancel")


# ============================================================================
# Tab Components
# ============================================================================


class ToolsTab(VerticalScroll):
    """Tools editor tab"""

    def compose(self) -> ComposeResult:
        yield Label("💡 Tip: Start with the simplest possible tool and expand later", classes="hint")
        yield Label("⚠️  Important: Only edit prompts here - don't change Python code structure", classes="warning")

        yield Horizontal(
            Select(
                [(t, t) for t in get_tools()],
                prompt="Select tool to edit",
                id="tool-select",
            ),
            Button("Add New Tool", id="add-tool"),
            classes="tool-controls",
        )

        yield Label(
            "⌨️  Editor shortcuts: Ctrl+Z (undo), Ctrl+Y (redo), Ctrl+A (select all), Ctrl+C/V (copy/paste)",
            classes="hint-small"
        )

        yield TextArea(
            "",
            language="python",
            id="tool-editor",
            show_line_numbers=True,
        )

        yield Horizontal(
            Button("💾 Save (Ctrl+S)", id="save-tool", variant="primary"),
            Label("💡 Tip: Save often when you find something good", classes="hint-inline"),
            Button("Delete Tool", id="delete-tool", variant="error"),
            classes="action-bar",
        )

        yield Label(
            "💡 Advanced: You can also edit tool files directly in agent_v3/tools/{tool_name}/prompts.py",
            classes="hint-small",
            id="direct-edit-hint"
        )


class MainPromptTab(VerticalScroll):
    """Main orchestrator prompt editor tab"""

    def compose(self) -> ComposeResult:
        yield Label("⚠️  Important: Don't forget to update this when adding/removing tools", classes="warning")
        yield Label(
            "💡 Best Practice: Use main system prompt only for giving necessary context about tools.\n"
            "Put detailed instructions in tool-specific prompts. This allows good context management\n"
            "without poisoning the orchestrator's chain of messages.",
            classes="hint"
        )

        yield TextArea(
            "",
            language="python",
            id="main-editor",
            show_line_numbers=True,
        )

        yield Horizontal(
            Button("💾 Save (Ctrl+S)", id="save-main", variant="primary"),
            Label("💡 Tip: Save often when you find something good", classes="hint-inline"),
            classes="action-bar",
        )


class TestAgentTab(VerticalScroll):
    """Test agent with embedded terminal"""

    def compose(self) -> ComposeResult:
        yield Label("💡 Tip: Test your prompts often", classes="hint")

        yield Horizontal(
            Button("▶️  Run Agent", id="run-agent", variant="success"),
            Button("⏹  Stop Agent", id="stop-agent", variant="error", disabled=True),
            classes="action-bar",
        )

        yield Label("Output:", classes="section-title")
        yield RichLog(id="agent-output", highlight=True, markup=True)

        yield Label("Input:", classes="section-title")
        yield Input(
            placeholder="Type message to send to agent (press Enter to send)...",
            id="agent-input",
            disabled=True
        )


class HistoryTab(VerticalScroll):
    """Git history viewer"""

    def compose(self) -> ComposeResult:
        yield Label("Git History", classes="section-title")
        yield Horizontal(
            Button("Refresh", id="refresh-history"),
            classes="action-bar",
        )
        yield RichLog(id="git-log", highlight=True, markup=True)


# ============================================================================
# Main App
# ============================================================================


class AgentToolManager(App):
    """TUI app for managing agent tools"""

    CSS = """
    #staging-modal, #add-tool-modal {
        align: center middle;
        background: $panel;
        border: thick $primary;
        width: 60;
        height: auto;
        padding: 2;
    }

    #quit-modal {
        align: center middle;
        background: $panel;
        border: thick $error;
        width: 80;
        height: auto;
        padding: 2;
    }

    #modal-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .section-label {
        text-style: bold;
        margin: 1 0;
    }

    .file-item, .commit-item {
        color: $text-muted;
        margin-left: 2;
    }

    .hint {
        color: $accent;
        margin: 1 0;
    }

    .hint-small {
        color: $accent;
        margin: 0 0;
        text-style: dim;
    }

    .warning {
        color: $warning;
        margin: 1 0;
    }

    .hint-inline {
        color: $accent;
        padding: 0 2;
    }

    .section-title {
        text-style: bold;
        margin: 1 0;
    }

    .tool-controls {
        height: auto;
        margin: 1 0;
    }

    .action-bar {
        height: auto;
        margin: 1 0;
    }

    TextArea {
        height: 30;
        margin: 1 0;
    }

    RichLog {
        height: 20;
        border: solid $primary;
        margin: 1 0;
    }

    #branch-bar {
        background: $boost;
        height: auto;
        padding: 1;
        margin-bottom: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+q", "request_quit", "Quit"),
        Binding("ctrl+s", "save", "Save"),
        Binding("ctrl+n", "new_tool", "New Tool"),
    ]

    # Reactive state
    current_branch: reactive[str] = reactive("")
    is_staging: reactive[bool] = reactive(False)
    selected_tool: reactive[Optional[str]] = reactive(None)
    agent_process: Optional[subprocess.Popen] = None

    def on_mount(self) -> None:
        """Initialize app"""
        self.current_branch = get_current_branch()
        self.is_staging = self.current_branch and self.current_branch.startswith('staging-')

        # Maximize the tabbed content
        try:
            tabs = self.query_one(TabbedContent)
            self.maximize(tabs)
        except:
            pass

        if not self.is_staging:
            self.push_screen(CreateStagingModal(), self.on_staging_created)
        else:
            self.load_main_prompt()
            self.load_history()

    def on_staging_created(self, created: bool) -> None:
        """Callback after staging modal"""
        if created:
            self.refresh_branch_bar()
            self.load_main_prompt()
            self.load_history()

    def on_unmount(self) -> None:
        """Cleanup on app exit - checkout to original branch if still in staging"""
        # Kill agent process if still running
        if self.agent_process:
            try:
                self.agent_process.terminate()
                self.agent_process.wait(timeout=2)
            except:
                pass

        # Checkout to original branch if still in staging
        current = get_current_branch()
        if current and current.startswith('staging-'):
            # User killed the app without using quit modal
            # Checkout to original branch but keep staging branch for safety
            original = get_original_branch(current)
            run_git(['git', 'checkout', original])
            # Don't delete staging branch - user might want to come back to it

    def compose(self) -> ComposeResult:
        """Compose app layout"""
        yield Header()

        # Branch info bar
        with Container(id="branch-bar"):
            if self.is_staging:
                original = get_original_branch(self.current_branch)
                yield Horizontal(
                    Label(f"🧪 STAGING: {self.current_branch} (from {original})"),
                    Button(f"✅ Merge to {original}", id="merge"),
                    Button("🗑️  Discard", id="discard"),
                )
            else:
                yield Label(f"📍 Branch: {self.current_branch}")

        # Main tabbed interface
        with TabbedContent():
            with TabPane("🔧 Tools"):
                yield ToolsTab()
            with TabPane("📋 Main Prompt"):
                yield MainPromptTab()
            with TabPane("🚀 Test Agent"):
                yield TestAgentTab()
            with TabPane("📜 History"):
                yield HistoryTab()

        yield Footer()

    def refresh_branch_bar(self) -> None:
        """Refresh branch info bar"""
        self.current_branch = get_current_branch()
        self.is_staging = self.current_branch and self.current_branch.startswith('staging-')
        self.refresh(layout=True)

    # ========================================================================
    # Event Handlers
    # ========================================================================

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses"""
        if event.button.id == "merge":
            self.merge_staging()
        elif event.button.id == "discard":
            self.discard_staging()
        elif event.button.id == "add-tool":
            self.action_new_tool()
        elif event.button.id == "save-tool":
            self.save_tool()
        elif event.button.id == "delete-tool":
            self.delete_tool()
        elif event.button.id == "save-main":
            self.save_main_prompt()
        elif event.button.id == "run-agent":
            self.run_agent()
        elif event.button.id == "stop-agent":
            self.stop_agent()
        elif event.button.id == "refresh-history":
            self.load_history()

    def on_select_changed(self, event: Select.Changed) -> None:
        """Handle tool selection"""
        if event.select.id == "tool-select" and event.value != Select.BLANK:
            self.selected_tool = event.value
            self.load_tool(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle input submission (send to agent)"""
        if event.input.id == "agent-input" and self.agent_process:
            message = event.value.strip()
            if message:
                # Send to agent stdin
                try:
                    self.agent_process.stdin.write(message + "\n")
                    self.agent_process.stdin.flush()

                    # Show in output
                    log = self.query_one("#agent-output", RichLog)
                    log.write(f"[bold cyan]> {message}[/bold cyan]")

                    # Clear input
                    event.input.value = ""
                except Exception as e:
                    self.notify(f"Error sending input: {e}", severity="error")

    # ========================================================================
    # Actions
    # ========================================================================

    def action_save(self) -> None:
        """Save current file (Ctrl+S)"""
        # Check which tab is active
        try:
            if self.query_one("#tool-editor", TextArea):
                self.save_tool()
        except:
            pass

        try:
            if self.query_one("#main-editor", TextArea):
                self.save_main_prompt()
        except:
            pass

    def action_new_tool(self) -> None:
        """Create new tool (Ctrl+N)"""
        self.push_screen(AddToolModal(), self.on_tool_created)

    def action_request_quit(self) -> None:
        """Request quit with check for unsaved changes"""
        # If not in staging, just quit
        if not self.is_staging:
            self.exit()
            return

        # Check for uncommitted files
        uncommitted = get_uncommitted_files()

        # Check for unmerged commits
        original = get_original_branch(self.current_branch)
        unmerged = get_unmerged_commits(self.current_branch, original)

        # If no changes, just quit and discard staging
        if not uncommitted and not unmerged:
            # Silently discard empty staging branch
            run_git(['git', 'checkout', original])
            run_git(['git', 'branch', '-D', self.current_branch])
            self.exit()
            return

        # Show confirmation modal with changes
        self.push_screen(
            QuitConfirmModal(uncommitted, unmerged, original),
            self.on_quit_confirmed
        )

    def on_quit_confirmed(self, action: str) -> None:
        """Handle quit confirmation response"""
        if action == "cancel":
            return

        original = get_original_branch(self.current_branch)

        if action == "merge":
            run_git(['git', 'checkout', original])
            run_git(['git', 'merge', self.current_branch, '--no-ff', '-m', f'Merge {self.current_branch}'])
            run_git(['git', 'branch', '-D', self.current_branch])
            self.exit()
        elif action == "discard":
            run_git(['git', 'checkout', original])
            run_git(['git', 'branch', '-D', self.current_branch])
            self.exit()

    # ========================================================================
    # Git Operations
    # ========================================================================

    def merge_staging(self) -> None:
        """Merge staging branch to original"""
        original = get_original_branch(self.current_branch)

        run_git(['git', 'checkout', original])
        run_git(['git', 'merge', self.current_branch, '--no-ff', '-m', f'Merge {self.current_branch}'])
        run_git(['git', 'branch', '-D', self.current_branch])

        self.notify(f"Merged to {original} and deleted staging branch", severity="information")
        self.exit()

    def discard_staging(self) -> None:
        """Discard staging branch"""
        original = get_original_branch(self.current_branch)

        run_git(['git', 'checkout', original])
        run_git(['git', 'branch', '-D', self.current_branch])

        self.notify(f"Discarded staging branch", severity="information")
        self.exit()

    # ========================================================================
    # Tool Operations
    # ========================================================================

    def load_tool(self, tool_name: str) -> None:
        """Load tool prompts into editor"""
        prompts_file = f"agent_v3/tools/{tool_name}/prompts.py"
        content = read_file(prompts_file)

        editor = self.query_one("#tool-editor", TextArea)
        editor.text = content

        # Update the direct edit hint with actual file path
        try:
            hint = self.query_one("#direct-edit-hint", Label)
            hint.update(f"💡 Advanced: You can also edit this file directly at {prompts_file}")
        except:
            pass

        self.notify(f"Loaded {tool_name}")

    def save_tool(self) -> None:
        """Save current tool"""
        if not self.selected_tool:
            self.notify("No tool selected", severity="warning")
            return

        editor = self.query_one("#tool-editor", TextArea)
        content = editor.text

        prompts_file = f"agent_v3/tools/{self.selected_tool}/prompts.py"
        success, error = write_file(prompts_file, content)

        if success:
            run_git(['git', 'add', prompts_file])
            run_git(['git', 'commit', '-m', f'Update {self.selected_tool} prompts'])
            self.notify(f"Saved and committed {self.selected_tool}", severity="information")
        else:
            self.notify(f"Error saving: {error}", severity="error")

    def delete_tool(self) -> None:
        """Delete current tool"""
        if not self.selected_tool:
            self.notify("No tool selected", severity="warning")
            return

        tool_dir = f"agent_v3/tools/{self.selected_tool}"
        run_git(['git', 'rm', '-rf', tool_dir])
        run_git(['git', 'commit', '-m', f'Delete tool: {self.selected_tool}'])

        self.notify(f"Deleted {self.selected_tool}", severity="information")

        # Refresh tool list
        select = self.query_one("#tool-select", Select)
        select.set_options([(t, t) for t in get_tools()])

        # Clear editor
        editor = self.query_one("#tool-editor", TextArea)
        editor.text = ""
        self.selected_tool = None

    def on_tool_created(self, tool_name: Optional[str]) -> None:
        """Callback after tool creation"""
        if not tool_name:
            return

        tool_dir = Path(f"agent_v3/tools/{tool_name}")
        tool_dir.mkdir(exist_ok=True)

        # Create __init__.py
        class_name = tool_name.replace('_', ' ').title().replace(' ', '')
        init_content = f'''"""
{tool_name.replace('_', ' ').title()} tool
"""
from .main import {class_name}

__all__ = ['{class_name}']
'''
        write_file(tool_dir / "__init__.py", init_content)

        # Create prompts.py
        prompts_content = f'''"""
Prompts for {tool_name} tool
"""


def get_orchestrator_info() -> str:
    """Return tool description for orchestrator system prompt"""
    return """- {tool_name}: [Description here]
  Parameters: {{"request": "natural language description"}}"""


def get_system_prompt(**variables) -> str:
    """Return system prompt for LLM"""
    return f"""You are a [tool purpose here].

TASK: [What this tool does]

CRITICAL: Output ONLY the result. No explanations.
"""
'''
        write_file(tool_dir / "prompts.py", prompts_content)

        # Create main.py
        main_content = f'''"""
{tool_name.replace('_', ' ').title()} tool
"""
from typing import Dict, Any
from agent_v3.tools.base import Tool, ToolResult
from . import prompts


class {class_name}(Tool):
    """[Tool description]"""

    def __init__(self):
        super().__init__(
            name="{tool_name}",
            description="[Tool description]"
        )

    @classmethod
    def get_orchestrator_info(cls) -> str:
        return prompts.get_orchestrator_info()

    @classmethod
    def get_system_prompt(cls, **variables) -> str:
        return prompts.get_system_prompt(**variables)

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Execute tool logic"""
        # TODO: Implement tool logic
        return ToolResult(
            success=True,
            data={{"result": "Not implemented"}},
            error=None
        )
'''
        write_file(tool_dir / "main.py", main_content)

        # Commit
        run_git(['git', 'add', str(tool_dir)])
        run_git(['git', 'commit', '-m', f'Add new tool: {tool_name}'])

        self.notify(f"Created tool: {tool_name}", severity="information")

        # Refresh tool list and select new tool
        select = self.query_one("#tool-select", Select)
        select.set_options([(t, t) for t in get_tools()])
        select.value = tool_name

    # ========================================================================
    # Main Prompt Operations
    # ========================================================================

    def load_main_prompt(self) -> None:
        """Load main system prompt"""
        system_prompt_file = "agent_v3/prompts/system_prompt.py"
        content = read_file(system_prompt_file)

        try:
            editor = self.query_one("#main-editor", TextArea)
            editor.text = content
        except:
            pass  # Editor not ready yet

    def save_main_prompt(self) -> None:
        """Save main system prompt"""
        editor = self.query_one("#main-editor", TextArea)
        content = editor.text

        system_prompt_file = "agent_v3/prompts/system_prompt.py"
        success, error = write_file(system_prompt_file, content)

        if success:
            run_git(['git', 'add', system_prompt_file])
            run_git(['git', 'commit', '-m', 'Update main orchestrator prompt'])
            self.notify("Saved and committed main prompt", severity="information")
        else:
            self.notify(f"Error saving: {error}", severity="error")

    # ========================================================================
    # Agent Testing
    # ========================================================================

    def run_agent(self) -> None:
        """Run agent in embedded terminal"""
        if self.agent_process:
            self.notify("Agent already running", severity="warning")
            return

        # Clear output
        log = self.query_one("#agent-output", RichLog)
        log.clear()

        # Start process
        try:
            self.agent_process = subprocess.Popen(
                ["python", "-m", "agent_v3.main"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                env={**os.environ, "DEBUG": "1"}
            )

            # Enable input and stop button
            self.query_one("#agent-input", Input).disabled = False
            self.query_one("#run-agent", Button).disabled = True
            self.query_one("#stop-agent", Button).disabled = False

            # Start output reader thread
            self.start_agent_output_reader()

            self.notify("Agent started", severity="information")
        except Exception as e:
            self.notify(f"Error starting agent: {e}", severity="error")

    def start_agent_output_reader(self) -> None:
        """Read agent output in background thread"""
        def read_output():
            try:
                for line in iter(self.agent_process.stdout.readline, ''):
                    if line:
                        self.call_from_thread(self.append_agent_output, line.rstrip())
                    if self.agent_process.poll() is not None:
                        break

                # Process ended
                self.call_from_thread(self.on_agent_stopped)
            except Exception as e:
                self.call_from_thread(self.notify, f"Output reader error: {e}", severity="error")

        thread = threading.Thread(target=read_output, daemon=True)
        thread.start()

    def append_agent_output(self, line: str) -> None:
        """Append line to agent output"""
        log = self.query_one("#agent-output", RichLog)
        log.write(line)

    def stop_agent(self) -> None:
        """Stop running agent"""
        if self.agent_process:
            self.agent_process.terminate()
            self.agent_process.wait(timeout=5)
            self.agent_process = None
            self.on_agent_stopped()
            self.notify("Agent stopped", severity="information")

    def on_agent_stopped(self) -> None:
        """Cleanup when agent stops"""
        self.agent_process = None
        try:
            self.query_one("#agent-input", Input).disabled = True
            self.query_one("#run-agent", Button).disabled = False
            self.query_one("#stop-agent", Button).disabled = True
        except:
            pass

    # ========================================================================
    # History Operations
    # ========================================================================

    def load_history(self) -> None:
        """Load git history"""
        log_output, error = run_git(['git', 'log', '-20', '--pretty=format:%h|%an|%ar|%s'])

        try:
            log = self.query_one("#git-log", RichLog)
            log.clear()

            if log_output:
                for line in log_output.strip().split('\n'):
                    if line:
                        parts = line.split('|', 3)
                        if len(parts) == 4:
                            hash, author, time, msg = parts
                            log.write(f"[bold yellow]{hash}[/bold yellow] {msg}")
                            log.write(f"  [dim]{author} • {time}[/dim]\n")
            else:
                log.write(f"[red]Error: {error}[/red]")
        except:
            pass  # Log not ready yet


# ============================================================================
# Entry Point
# ============================================================================


if __name__ == "__main__":
    app = AgentToolManager()
    app.run()
