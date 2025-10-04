"""
Minimal Streamlit app for agent_v3 tool and prompt management
Run: streamlit run app.py
"""
import streamlit as st
from pathlib import Path
from agent_v3.tools import ToolRegistry, ToolGenerator
from agent_v3.prompts.loader import PromptLoader

# Page config
st.set_page_config(page_title="Agent Tool Manager", layout="wide")
st.title("🤖 Agent Tool Manager")

# Initialize
@st.cache_resource
def get_generator():
    return ToolGenerator()

@st.cache_resource
def get_loader():
    return PromptLoader()

gen = get_generator()
loader = get_loader()

# Tabs
tab1, tab2, tab3 = st.tabs(["📋 Tools", "✏️ Prompts", "➕ Generate"])

# ============================================================================
# TAB 1: TOOLS
# ============================================================================
with tab1:
    st.header("Registered Tools")

    tools = ToolRegistry.get_all_tools()

    col1, col2 = st.columns([1, 2])

    with col1:
        st.metric("Total Tools", len(tools))

        selected_tool = st.selectbox(
            "Select Tool",
            options=list(tools.keys()),
            key="tool_selector"
        )

    with col2:
        if selected_tool:
            tool = tools[selected_tool]

            st.subheader(f"Tool: {selected_tool}")
            st.text(f"Description: {tool.description}")

            # Validation
            error = ToolRegistry.validate_tool(tool)
            if error:
                st.error(f"❌ Validation Error: {error}")
            else:
                st.success("✅ Tool is valid")

            # Delete button (only for generated tools, not core tools)
            core_tools = ["text_to_sql_rx", "text_to_sql_med", "text_to_sql_provider_payments",
                         "text_to_sql_providers_bio", "bigquery_sql_query", "communicate", "complete"]

            if selected_tool not in core_tools:
                st.divider()
                if st.button(f"🗑️ Delete {selected_tool}", type="secondary"):
                    error = gen.delete_tool(selected_tool)
                    if error:
                        st.error(f"Failed to delete: {error}")
                    else:
                        st.success(f"Deleted {selected_tool}")
                        st.rerun()

# ============================================================================
# TAB 2: PROMPTS
# ============================================================================
with tab2:
    st.header("Edit Prompts")

    # List available prompts
    prompts_dir = Path("agent_v3/prompts/tools")
    prompt_files = sorted(prompts_dir.glob("*.yaml"))

    col1, col2 = st.columns([1, 3])

    with col1:
        st.metric("Available Prompts", len(prompt_files))

        selected_prompt_file = st.selectbox(
            "Select Prompt",
            options=prompt_files,
            format_func=lambda x: x.stem,
            key="prompt_selector"
        )

    with col2:
        if selected_prompt_file:
            st.subheader(f"Editing: {selected_prompt_file.name}")

            # Read file
            with open(selected_prompt_file, 'r') as f:
                content = f.read()

            # Editor
            edited_content = st.text_area(
                "YAML Content",
                value=content,
                height=500,
                key="prompt_editor"
            )

            col_save, col_validate = st.columns(2)

            with col_validate:
                if st.button("🔍 Validate", key="validate_prompt"):
                    error = loader.validate_prompt_file(selected_prompt_file)
                    if error:
                        st.error(f"❌ {error}")
                    else:
                        st.success("✅ Valid YAML")

            with col_save:
                if st.button("💾 Save", type="primary", key="save_prompt"):
                    try:
                        with open(selected_prompt_file, 'w') as f:
                            f.write(edited_content)
                        st.success(f"✅ Saved {selected_prompt_file.name}")

                        # Git commit
                        if st.checkbox("Commit to git", value=True, key="commit_prompt"):
                            import subprocess
                            msg = st.text_input("Commit message:", f"Update prompt: {selected_prompt_file.stem}")
                            if msg:
                                subprocess.run(["git", "add", str(selected_prompt_file)])
                                subprocess.run(["git", "commit", "-m", msg])
                                st.success("✅ Committed")
                    except Exception as e:
                        st.error(f"❌ Failed to save: {e}")

# ============================================================================
# TAB 3: GENERATE
# ============================================================================
with tab3:
    st.header("Generate New Tool")

    # Template selection
    templates = gen.list_templates()
    template_type = st.selectbox("Template Type", templates, key="template_type")

    if template_type:
        schema = gen.get_template_schema(template_type)

        st.subheader("Configuration")

        # Form
        with st.form("tool_config_form"):
            tool_name = st.text_input("Tool Name*", placeholder="text_to_sql_pharmacy")
            class_name = st.text_input("Class Name*", placeholder="TextToSQLPharmacy")
            description = st.text_input("Description*", placeholder="Generate SQL for pharmacy data")
            table_name = st.text_input("Table Name*", placeholder="`project.dataset.table`")

            st.subheader("Columns")
            num_cols = st.number_input("Number of columns", min_value=1, max_value=20, value=3)

            columns = []
            for i in range(num_cols):
                col1, col2, col3 = st.columns(3)
                with col1:
                    col_name = st.text_input(f"Column {i+1} Name", key=f"col_name_{i}")
                with col2:
                    col_type = st.selectbox(f"Type", ["STRING", "INTEGER", "FLOAT", "DATE", "BOOLEAN"], key=f"col_type_{i}")
                with col3:
                    col_desc = st.text_input(f"Description", key=f"col_desc_{i}")

                if col_name:
                    columns.append({"name": col_name, "type": col_type, "description": col_desc})

            st.subheader("Optional Settings")

            column_priority = st.text_area(
                "Column Selection Priority",
                value="- Be selective with columns\n- NEVER use SELECT *"
            )

            agg_rules_text = st.text_area(
                "Aggregation Rules (one per line)",
                value="- Use appropriate GROUP BY clauses"
            )
            agg_rules = [line.strip() for line in agg_rules_text.split('\n') if line.strip()]

            date_filtering = st.text_area("Date Filtering (optional)", "")
            item_matching = st.text_area("Item Matching (optional)", "")

            col_preview, col_create = st.columns(2)

            with col_preview:
                preview = st.form_submit_button("🔍 Preview")

            with col_create:
                create = st.form_submit_button("✅ Create", type="primary")

            if preview or create:
                # Build config
                config = {
                    "tool_name": tool_name,
                    "class_name": class_name,
                    "description": description,
                    "table_name": table_name,
                    "key_columns": columns,
                    "column_selection_priority": column_priority,
                    "aggregation_rules": agg_rules,
                }

                if date_filtering:
                    config["date_filtering"] = date_filtering
                if item_matching:
                    config["item_matching"] = item_matching

                # Validate
                error = gen.validate_config(template_type, config)
                if error:
                    st.error(f"❌ Validation Error: {error}")
                else:
                    if preview:
                        # Preview
                        code, yaml, err = gen.preview_tool(template_type, config)
                        if err:
                            st.error(f"❌ {err}")
                        else:
                            st.success("✅ Generated successfully")

                            col1, col2 = st.columns(2)
                            with col1:
                                st.subheader("Python Code")
                                st.code(code, language="python")
                            with col2:
                                st.subheader("YAML Prompt")
                                st.code(yaml, language="yaml")

                    elif create:
                        # Create files
                        py_path, yaml_path, err = gen.create_tool(template_type, config)
                        if err:
                            st.error(f"❌ {err}")
                        else:
                            st.success(f"✅ Created tool files:")
                            st.code(f"Python: {py_path}\nPrompt: {yaml_path}")

                            # Git commit option
                            if st.checkbox("Commit to git", value=True, key="commit_new_tool"):
                                import subprocess
                                msg = st.text_input("Commit message:", f"Add new tool: {tool_name}")
                                if msg:
                                    subprocess.run(["git", "add", py_path, yaml_path])
                                    subprocess.run(["git", "commit", "-m", msg])
                                    st.success("✅ Committed")

# Footer
st.divider()
st.caption("Agent V3 Tool Manager | Minimal Streamlit Interface")
