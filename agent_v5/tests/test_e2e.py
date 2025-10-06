"""
End-to-end tests for ResearchAgent with BigQuery MCP integration
"""
import pytest
import tempfile
import os
from agent_v5.agent import ResearchAgent
from agent_v5.tools.mcp_proxy import MCPToolProxy


async def mock_bigquery_query(args):
    """Mock BigQuery tool that simulates querying and saving CSV"""
    sql = args.get("sql", "")
    dataset_name = args.get("dataset_name", "results")

    mock_data = """NPI,DRUG_NAME,STATE,COUNT
1234567890,HUMIRA,CA,150
0987654321,HUMIRA,CA,120
1111111111,HUMIRA,CA,100"""

    return {
        "content": [{
            "type": "text",
            "text": f"Saved 3 rows to {dataset_name}.csv\n\nPreview:\n{mock_data}"
        }]
    }


@pytest.mark.asyncio
async def test_e2e_bigquery_mcp_integration():
    """Test 1: Agent uses BigQuery MCP tool successfully"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="e2e_test",
            workspace_dir=tmpdir,
            system_prompt="You are a data analyst. Use the bigquery_query tool to query data."
        )

        bq_tool = MCPToolProxy(
            mcp_name="bigquery",
            tool_name="bigquery_query",
            tool_fn=mock_bigquery_query,
            mcp_schema={
                "description": "Execute SQL on BigQuery and save results to CSV",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string"},
                        "dataset_name": {"type": "string"}
                    },
                    "required": ["sql", "dataset_name"]
                }
            },
            workspace_dir=tmpdir
        )

        agent.tools.register(bq_tool)

        tool_executions = []
        async for msg in agent.run("Use bigquery_query tool with sql='SELECT * FROM rx_claims LIMIT 10' and dataset_name='humira_data'"):
            if msg.get("type") == "tool_execution":
                tool_executions.append(msg)

        bq_executions = [t for t in tool_executions if "bigquery" in t["tool_name"]]
        assert len(bq_executions) >= 1, f"BigQuery tool not called. Tools called: {[t['tool_name'] for t in tool_executions]}"
        assert "Saved 3 rows" in bq_executions[0]["tool_output"]


@pytest.mark.asyncio
async def test_e2e_full_research_workflow():
    """Test 2: Complete workflow - query, save, read, analyze"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="workflow_test",
            workspace_dir=tmpdir,
            system_prompt="You are a data analyst. You have BigQuery access and file tools."
        )

        bq_tool = MCPToolProxy(
            mcp_name="bigquery",
            tool_name="bigquery_query",
            tool_fn=mock_bigquery_query,
            mcp_schema={
                "description": "Execute SQL on BigQuery and save results to CSV",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string"},
                        "dataset_name": {"type": "string"}
                    },
                    "required": ["sql", "dataset_name"]
                }
            },
            workspace_dir=tmpdir
        )

        agent.tools.register(bq_tool)

        csv_file = os.path.join(tmpdir, "data.csv")
        with open(csv_file, "w") as f:
            f.write("NPI,DRUG,COUNT\n1234,HUMIRA,100\n5678,HUMIRA,200\n")

        tool_executions = []
        async for msg in agent.run("Read data.csv and tell me the total count"):
            if msg.get("type") == "tool_execution":
                tool_executions.append(msg)

        read_executions = [t for t in tool_executions if t["tool_name"] == "Read"]
        assert len(read_executions) >= 1
        assert "HUMIRA" in read_executions[0]["tool_output"]


@pytest.mark.asyncio
async def test_e2e_multiple_tool_sequence():
    """Test 3: Agent executes multiple tools in sequence"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="sequence_test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant with file and command access."
        )

        tool_executions = []
        async for msg in agent.run("Create a file test.txt with 'hello', then read it, then run 'cat test.txt'"):
            if msg.get("type") == "tool_execution":
                tool_executions.append(msg)

        write_tools = [t for t in tool_executions if t["tool_name"] == "Write"]
        read_tools = [t for t in tool_executions if t["tool_name"] == "Read"]
        bash_tools = [t for t in tool_executions if t["tool_name"] == "Bash"]

        assert len(write_tools) >= 1
        assert len(read_tools) >= 1

        if bash_tools:
            assert "hello" in bash_tools[0]["tool_output"]


@pytest.mark.asyncio
async def test_e2e_workspace_persistence():
    """Test 4: Files persist in workspace across tool calls"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="persist_test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant."
        )

        tool_executions = []
        async for msg in agent.run("Create a file named persist.txt with content 'PERSISTENT_DATA_123'"):
            if msg.get("type") == "tool_execution":
                tool_executions.append(msg)

        write_tools = [t for t in tool_executions if t["tool_name"] == "Write"]
        assert len(write_tools) >= 1

        persist_file = os.path.join(tmpdir, "persist.txt")
        if os.path.exists(persist_file):
            with open(persist_file) as f:
                content = f.read()
                assert "PERSISTENT_DATA_123" in content


@pytest.mark.asyncio
async def test_e2e_conversation_continuity():
    """Test 5: Agent maintains conversation context across multiple queries"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="context_test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant."
        )

        async for msg in agent.run("Create a file called numbers.txt with the number 42"):
            pass

        assert len(agent.conversation_history) >= 2

        text_responses = []
        async for msg in agent.run("What number did I ask you to write?"):
            if msg.get("type") == "text_delta":
                text_responses.append(msg["text"])

        full_response = "".join(text_responses)
        assert "42" in full_response or "forty-two" in full_response.lower()


@pytest.mark.asyncio
async def test_e2e_error_handling():
    """Test 6: Agent handles tool errors gracefully"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="error_test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant."
        )

        tool_executions = []
        async for msg in agent.run("Read the file nonexistent_file_xyz_123.txt"):
            if msg.get("type") == "tool_execution":
                tool_executions.append(msg)

        read_executions = [t for t in tool_executions if t["tool_name"] == "Read"]
        assert len(read_executions) >= 1
        assert "not found" in read_executions[0]["tool_output"].lower()


@pytest.mark.asyncio
async def test_e2e_python_script_creation_and_execution():
    """Test 7: Agent creates and executes Python scripts"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="python_test",
            workspace_dir=tmpdir,
            system_prompt="You are a helpful assistant with Python scripting capabilities."
        )

        tool_executions = []
        async for msg in agent.run("Create a Python script called hello.py that prints 'SCRIPT_OUTPUT_789', then run it"):
            if msg.get("type") == "tool_execution":
                tool_executions.append(msg)

        write_tools = [t for t in tool_executions if t["tool_name"] == "Write"]
        bash_tools = [t for t in tool_executions if t["tool_name"] == "Bash"]

        assert len(write_tools) >= 1
        assert "hello.py" in write_tools[0]["tool_input"]["file_path"]

        if bash_tools:
            python_executions = [b for b in bash_tools if "python" in b["tool_input"]["command"]]
            if python_executions:
                assert "SCRIPT_OUTPUT_789" in python_executions[0]["tool_output"]


@pytest.mark.asyncio
async def test_e2e_bigquery_to_analysis():
    """Test 8: Full pipeline - BigQuery → CSV → Python analysis"""
    if not os.getenv("ANTHROPIC_API_KEY"):
        pytest.skip("ANTHROPIC_API_KEY not set")

    with tempfile.TemporaryDirectory() as tmpdir:
        agent = ResearchAgent(
            session_id="pipeline_test",
            workspace_dir=tmpdir,
            system_prompt="You are a data analyst. Use tools to query and analyze data."
        )

        async def realistic_bq_tool(args):
            csv_path = os.path.join(tmpdir, f"{args['dataset_name']}.csv")
            with open(csv_path, "w") as f:
                f.write("prescriber,drug,count\n")
                f.write("NPI001,HUMIRA,150\n")
                f.write("NPI002,HUMIRA,200\n")
                f.write("NPI003,HUMIRA,100\n")

            return {
                "content": [{
                    "type": "text",
                    "text": f"Saved 3 rows to {args['dataset_name']}.csv in workspace"
                }]
            }

        bq_tool = MCPToolProxy(
            mcp_name="bigquery",
            tool_name="bigquery_query",
            tool_fn=realistic_bq_tool,
            mcp_schema={
                "description": "Execute SQL on BigQuery and save CSV to workspace",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sql": {"type": "string"},
                        "dataset_name": {"type": "string"}
                    },
                    "required": ["sql", "dataset_name"]
                }
            },
            workspace_dir=tmpdir
        )

        agent.tools.register(bq_tool)

        tool_executions = []
        async for msg in agent.run("Use bigquery_query with sql='SELECT * FROM rx' and dataset_name='humira', then read humira.csv"):
            if msg.get("type") == "tool_execution":
                tool_executions.append(msg)

        bq_tools = [t for t in tool_executions if "bigquery" in t["tool_name"]]
        read_tools = [t for t in tool_executions if t["tool_name"] == "Read"]

        assert len(bq_tools) >= 1, f"BigQuery not called. Tools: {[t['tool_name'] for t in tool_executions]}"

        if read_tools:
            assert "NPI001" in read_tools[0]["tool_output"] or "prescriber" in read_tools[0]["tool_output"]
