"""
Streamlit app for managing agent tools with Git-based staging workflow
"""
import streamlit as st
import subprocess
import os
from pathlib import Path
from datetime import datetime


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


def main():
    st.set_page_config(page_title="Agent Tool Manager", layout="wide")

    # Check if in staging
    current_branch = get_current_branch()
    is_staging = current_branch and current_branch.startswith('staging-')

    # Header
    st.title("🛠️ Agent Tool Manager")

    if is_staging:
        original_branch = get_original_branch(current_branch)
        st.info(f"🧪 **STAGING MODE** - Branch: `{current_branch}` (from `{original_branch}`)")

        col1, col2, col3 = st.columns([1, 1, 8])
        with col1:
            if st.button("✅ Merge to " + original_branch):
                run_git(['git', 'checkout', original_branch])
                run_git(['git', 'merge', current_branch, '--no-ff', '-m', f'Merge {current_branch}'])
                run_git(['git', 'branch', '-D', current_branch])
                st.success(f"Merged to {original_branch} and deleted staging branch")
                st.rerun()

        with col2:
            if st.button("🗑️ Discard staging"):
                run_git(['git', 'checkout', original_branch])
                run_git(['git', 'branch', '-D', current_branch])
                st.success("Discarded staging branch")
                st.rerun()
    else:
        st.caption(f"📍 Branch: `{current_branch}`")
        if st.button("🧪 Create Staging Environment"):
            staging = create_staging_branch(current_branch)
            st.success(f"Created staging branch: {staging}")
            st.rerun()
        st.stop()  # Don't show tabs if not in staging

    # Tabs
    tab1, tab2, tab3, tab4 = st.tabs(["🔧 Tools", "📋 Main Prompt", "🚀 Test Agent", "📜 History"])

    # Tab 1: Tools
    with tab1:
        st.header("Edit Tools")

        st.info("💡 **Tip:** Start with the simplest possible tool and expand later")
        st.warning("⚠️ **Important:** Only edit prompts here - don't change Python code structure")

        # Add new tool
        with st.expander("➕ Add New Tool"):
            new_tool_name = st.text_input("Tool name", placeholder="text_to_sql_custom")
            if st.button("Create Tool") and new_tool_name:
                tool_dir = Path(f"agent_v3/tools/{new_tool_name}")
                tool_dir.mkdir(exist_ok=True)

                # Create __init__.py
                init_content = f'''"""
{new_tool_name.replace('_', ' ').title()} tool
"""
from .main import {new_tool_name.replace('_', ' ').title().replace(' ', '')}

__all__ = ['{new_tool_name.replace('_', ' ').title().replace(' ', '')}']
'''
                write_file(tool_dir / "__init__.py", init_content)

                # Create prompts.py
                prompts_content = f'''"""
Prompts for {new_tool_name} tool
"""


def get_orchestrator_info() -> str:
    """Return tool description for orchestrator system prompt"""
    return """- {new_tool_name}: [Description here]
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
{new_tool_name.replace('_', ' ').title()} tool
"""
from typing import Dict, Any
from agent_v3.tools.base import Tool, ToolResult
from . import prompts


class {new_tool_name.replace('_', ' ').title().replace(' ', '')}(Tool):
    """[Tool description]"""

    def __init__(self):
        super().__init__(
            name="{new_tool_name}",
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
                run_git(['git', 'commit', '-m', f'Add new tool: {new_tool_name}'])

                st.success(f"Created tool: {new_tool_name}")
                st.rerun()

        st.divider()

        # Edit existing tools
        tools = get_tools()
        selected_tool = st.selectbox("Select tool to edit", tools)

        if selected_tool:
            prompts_file = f"agent_v3/tools/{selected_tool}/prompts.py"
            content = read_file(prompts_file)

            col1, col2 = st.columns(2)

            with col1:
                st.subheader("✏️ Edit")
                edited = st.text_area(
                    "Edit prompts.py",
                    value=content,
                    height=500,
                    key=f"edit_{selected_tool}",
                    label_visibility="collapsed"
                )

            with col2:
                st.subheader("👁️ Preview")
                st.code(edited, language='python', line_numbers=True)

            col_a, col_b = st.columns([1, 5])

            with col_a:
                if st.button("💾 Save", use_container_width=True, type="primary"):
                    success, error = write_file(prompts_file, edited)
                    if success:
                        run_git(['git', 'add', prompts_file])
                        run_git(['git', 'commit', '-m', f'Update {selected_tool} prompts'])
                        st.success("Saved and committed!")
                        st.rerun()
                    else:
                        st.error(f"Error: {error}")

            with col_b:
                st.caption("💡 **Tip:** Save often when you find something good")

            # Delete tool
            st.divider()
            with st.expander("⚠️ Delete Tool"):
                if st.button(f"Delete {selected_tool}", type="secondary"):
                    tool_dir = f"agent_v3/tools/{selected_tool}"
                    run_git(['git', 'rm', '-rf', tool_dir])
                    run_git(['git', 'commit', '-m', f'Delete tool: {selected_tool}'])
                    st.success(f"Deleted {selected_tool}")
                    st.rerun()

    # Tab 2: Main Prompt
    with tab2:
        st.header("Main Orchestrator Prompt")

        st.warning("⚠️ **Important:** Don't forget to update this when adding/removing tools")
        st.info("""💡 **Best Practice:** Use main system prompt only for giving necessary context about tools.
Put detailed instructions in tool-specific prompts. This allows good context management without poisoning the orchestrator's chain of messages.""")

        system_prompt_file = "agent_v3/prompts/system_prompt.py"
        content = read_file(system_prompt_file)

        col1, col2 = st.columns(2)

        with col1:
            st.subheader("✏️ Edit")
            edited = st.text_area(
                "Edit system_prompt.py",
                value=content,
                height=500,
                key="edit_main_prompt",
                label_visibility="collapsed"
            )

        with col2:
            st.subheader("👁️ Preview")
            st.code(edited, language='python', line_numbers=True)

        col_a, col_b = st.columns([1, 5])

        with col_a:
            if st.button("💾 Save", use_container_width=True, type="primary", key="save_main"):
                success, error = write_file(system_prompt_file, edited)
                if success:
                    run_git(['git', 'add', system_prompt_file])
                    run_git(['git', 'commit', '-m', 'Update main orchestrator prompt'])
                    st.success("Saved and committed!")
                    st.rerun()
                else:
                    st.error(f"Error: {error}")

        with col_b:
            st.caption("💡 **Tip:** Save often when you find something good")

    # Tab 3: Test Agent
    with tab3:
        st.header("Test Agent")

        st.info("💡 **Tip:** Test your prompts often")

        if st.button("▶️ Run Agent in Terminal", type="primary", use_container_width=True):
            # macOS - open Terminal.app with agent command
            script = f'''tell app "Terminal"
    do script "cd {os.getcwd()} && DEBUG=1 python -m agent_v3.main"
    activate
end tell'''

            subprocess.Popen(['osascript', '-e', script])
            st.success("✅ Opened agent in Terminal.app")

        st.divider()

        st.caption("Or run this command manually:")
        st.code(f"cd {os.getcwd()}\nDEBUG=1 python -m agent_v3.main")

    # Tab 4: History
    with tab4:
        st.header("Git History")

        limit = st.slider("Show last N commits", 5, 50, 10)

        log_output, _ = run_git(['git', 'log', f'-{limit}', '--pretty=format:%h|%an|%ar|%s'])

        if log_output:
            for line in log_output.strip().split('\n'):
                if line:
                    hash, author, time, msg = line.split('|', 3)

                    col1, col2, col3 = st.columns([1, 5, 1])

                    with col1:
                        st.code(hash)

                    with col2:
                        st.write(f"**{msg}**")
                        st.caption(f"{author} • {time}")

                    with col3:
                        if st.button("View", key=f"view_{hash}"):
                            diff_output, _ = run_git(['git', 'show', hash])
                            st.code(diff_output, language='diff')

                    st.divider()


if __name__ == "__main__":
    main()
