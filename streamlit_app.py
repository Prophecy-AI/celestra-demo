"""
Streamlit app for managing agent tools with Git-based versioning
"""
import streamlit as st
import subprocess
import os
from pathlib import Path
from datetime import datetime


def run_git_command(cmd):
    """Run git command and return output"""
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            cwd=os.getcwd()
        )
        if result.returncode != 0:
            return None, result.stderr
        return result.stdout, None
    except Exception as e:
        return None, str(e)


def get_tools():
    """Get list of all tools by scanning agent_v3/tools/"""
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

    st.title("🛠️ Agent Tool Manager")
    st.caption("Git-based version control for agent prompts")

    # Check git status
    status, error = run_git_command(['git', 'status', '--porcelain'])
    if error:
        st.error(f"Git error: {error}")
        return

    has_changes = bool(status and status.strip())

    # Tabs
    tab1, tab2, tab3 = st.tabs(["📝 Edit Prompts", "📜 Version History", "🚀 Run Agent"])

    # Tab 1: Edit Prompts
    with tab1:
        st.header("Edit Tool Prompts")

        tools = get_tools()
        if not tools:
            st.warning("No tools found in agent_v3/tools/")
            return

        col1, col2 = st.columns([1, 3])

        with col1:
            selected_tool = st.selectbox("Select Tool", tools)

            if has_changes:
                st.warning("⚠️ Uncommitted changes")
                if st.button("Discard all changes"):
                    run_git_command(['git', 'checkout', '.'])
                    st.rerun()

        with col2:
            if selected_tool:
                prompts_file = f"agent_v3/tools/{selected_tool}/prompts.py"

                # Read current content
                content = read_file(prompts_file)

                # Editor
                edited_content = st.text_area(
                    f"Edit {prompts_file}",
                    value=content,
                    height=500,
                    key=f"editor_{selected_tool}"
                )

                col_a, col_b, col_c = st.columns([2, 2, 6])

                with col_a:
                    if st.button("💾 Save", use_container_width=True):
                        success, error = write_file(prompts_file, edited_content)
                        if success:
                            st.success("Saved!")
                            st.rerun()
                        else:
                            st.error(f"Error: {error}")

                with col_b:
                    commit_msg = st.text_input("Commit message", value=f"Update {selected_tool} prompts")

                with col_c:
                    if st.button("📦 Commit", use_container_width=True, type="primary"):
                        # Add file
                        run_git_command(['git', 'add', prompts_file])
                        # Commit
                        output, error = run_git_command(['git', 'commit', '-m', commit_msg])
                        if error:
                            st.error(f"Commit failed: {error}")
                        else:
                            st.success(f"Committed: {commit_msg}")
                            st.rerun()

    # Tab 2: Version History
    with tab2:
        st.header("Version History")

        col1, col2 = st.columns([1, 3])

        with col1:
            history_tool = st.selectbox("Select Tool", tools, key="history_tool")
            limit = st.slider("Show last N commits", 5, 50, 10)

        with col2:
            if history_tool:
                prompts_file = f"agent_v3/tools/{history_tool}/prompts.py"

                # Get git log
                log_output, error = run_git_command([
                    'git', 'log',
                    f'-{limit}',
                    '--pretty=format:%h|%an|%ar|%s',
                    '--', prompts_file
                ])

                if error:
                    st.error(f"Error: {error}")
                elif not log_output:
                    st.info("No commit history found")
                else:
                    commits = []
                    for line in log_output.strip().split('\n'):
                        if line:
                            hash, author, time, msg = line.split('|', 3)
                            commits.append({
                                'hash': hash,
                                'author': author,
                                'time': time,
                                'message': msg
                            })

                    st.subheader("Commits")

                    for commit in commits:
                        col_a, col_b, col_c = st.columns([1, 4, 1])

                        with col_a:
                            st.code(commit['hash'])

                        with col_b:
                            st.write(f"**{commit['message']}**")
                            st.caption(f"{commit['author']} • {commit['time']}")

                        with col_c:
                            if st.button("↩️ Rollback", key=f"rollback_{commit['hash']}"):
                                output, error = run_git_command([
                                    'git', 'checkout',
                                    commit['hash'],
                                    '--', prompts_file
                                ])
                                if error:
                                    st.error(f"Rollback failed: {error}")
                                else:
                                    st.success(f"Rolled back to {commit['hash']}")
                                    # Commit the rollback
                                    run_git_command(['git', 'add', prompts_file])
                                    run_git_command(['git', 'commit', '-m', f"Rollback to {commit['hash']}: {commit['message']}"])
                                    st.rerun()

                        # Show diff on expand
                        with st.expander("View diff"):
                            diff_output, _ = run_git_command([
                                'git', 'show',
                                commit['hash'],
                                '--', prompts_file
                            ])
                            if diff_output:
                                st.code(diff_output, language='diff')

                        st.divider()

    # Tab 3: Run Agent
    with tab3:
        st.header("Agent Playground")

        st.info("💡 Run agent with current prompt state (staging environment)")

        # Show current git state
        branch_output, _ = run_git_command(['git', 'branch', '--show-current'])
        if branch_output:
            st.caption(f"📍 Branch: `{branch_output.strip()}`")

        if has_changes:
            st.warning("⚠️ You have uncommitted changes. Commit them first to test in staging.")

        col1, col2 = st.columns([2, 1])

        with col1:
            user_query = st.text_area(
                "Enter your query",
                placeholder="Find all prescribers of HUMIRA in California",
                height=100
            )

        with col2:
            st.write("**Agent Settings**")
            debug_mode = st.checkbox("Debug mode", value=True)
            max_iterations = st.number_input("Max iterations", 1, 20, 10)

        if st.button("▶️ Run Agent", type="primary", use_container_width=True):
            if not user_query:
                st.error("Please enter a query")
            else:
                st.subheader("Agent Output")

                # Build command
                cmd = ['python', '-m', 'agent_v3.main']
                if debug_mode:
                    cmd = ['DEBUG=1'] + cmd

                # Run agent
                with st.spinner("Running agent..."):
                    result = subprocess.run(
                        cmd,
                        input=user_query,
                        capture_output=True,
                        text=True,
                        env={**os.environ, 'DEBUG': '1' if debug_mode else '0'}
                    )

                    if result.stdout:
                        st.code(result.stdout, language='text')

                    if result.stderr:
                        st.error("Errors:")
                        st.code(result.stderr, language='text')

                    if result.returncode != 0:
                        st.error(f"Agent exited with code {result.returncode}")


if __name__ == "__main__":
    main()
