#!/usr/bin/env python3
"""
Local CLI for Agent V5 - No Modal required
Run locally with: python agent_v5/cli.py
"""
import os
import sys
import uuid
import json
import asyncio
import polars as pl
from pathlib import Path
from dotenv import load_dotenv
from google.oauth2 import service_account
from google.cloud import bigquery

from agent_v5.agent import ResearchAgent
from agent_v5.tools.mcp_proxy import MCPToolProxy


SYSTEM_PROMPT = """You are a healthcare data research engineer with direct BigQuery access.

**Available Dataset:**

RX_CLAIMS - Table: `unique-bonbon-472921-q8.Claims.rx_claims`
- PRESCRIBER_NPI_NBR: Prescriber NPI
- NDC_DRUG_NM: Drug name
- NDC_PREFERRED_BRAND_NM: Brand name
- PRESCRIBER_NPI_STATE_CD: State
- SERVICE_DATE_DD: Fill date
- DISPENSED_QUANTITY_VAL: Quantity

**Your Tools:**
- mcp__bigquery__bigquery_query: Execute SQL queries and save results to CSV in workspace
- Read: Read files from workspace
- Write: Create files and Python scripts
- Edit: Modify existing files
- Bash: Execute shell commands and run Python scripts
- Glob: Find files by pattern
- Grep: Search file contents

**Research Workflow:**
1. Understand the research question
2. Query BigQuery for relevant data
3. Analyze with Python/Polars if needed
4. Present findings clearly

**Guidelines:**
- Use plain English when explaining results
- Suggest follow-up analyses proactively
- Save intermediate results as CSV files
- Create visualizations when helpful

Current date: 2025-10-06"""


async def main():
    load_dotenv()

    GCP_PROJECT = os.getenv("GCP_PROJECT")
    GCP_CREDENTIALS_JSON = os.getenv("GCP_SERVICE_ACCOUNT_JSON")
    ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

    if not ANTHROPIC_API_KEY:
        print("❌ Missing ANTHROPIC_API_KEY in .env")
        sys.exit(1)

    if not GCP_PROJECT or not GCP_CREDENTIALS_JSON:
        print("⚠️  Warning: GCP credentials not found. BigQuery tool will not be available.")
        print("   Set GCP_PROJECT and GCP_SERVICE_ACCOUNT_JSON in .env to enable BigQuery.")
        gcp_credentials = None
    else:
        creds_dict = json.loads(GCP_CREDENTIALS_JSON)
        gcp_credentials = service_account.Credentials.from_service_account_info(creds_dict)

    session_id = str(uuid.uuid4())[:8]
    workspace_dir = Path(f"./workspace/{session_id}")
    workspace_dir.mkdir(parents=True, exist_ok=True)

    print("=" * 80)
    print("🤖 Agent V5 - Research Engineer (Local CLI)")
    print("=" * 80)
    print(f"Session: {session_id}")
    print(f"Workspace: {workspace_dir.absolute()}")
    if gcp_credentials:
        print("BigQuery: ✅ Enabled")
    else:
        print("BigQuery: ❌ Disabled (credentials not found)")
    print("Type 'exit' to quit")
    print("=" * 80)
    print()

    agent = ResearchAgent(
        session_id=session_id,
        workspace_dir=str(workspace_dir),
        system_prompt=SYSTEM_PROMPT
    )

    if gcp_credentials:
        async def bigquery_query_tool(args):
            """Execute SQL on BigQuery and save results to workspace"""
            client = bigquery.Client(project=GCP_PROJECT, credentials=gcp_credentials)
            query_job = client.query(args["sql"])
            results = query_job.result(timeout=30.0)

            arrow_table = results.to_arrow(create_bqstorage_client=False)
            df = pl.from_arrow(arrow_table)

            csv_path = workspace_dir / f"{args['dataset_name']}.csv"
            df.write_csv(str(csv_path))

            preview = str(df.head(10))
            return {
                "content": [{
                    "type": "text",
                    "text": f"Saved {df.shape[0]:,} rows to {args['dataset_name']}.csv\n\n{preview}"
                }]
            }

        bq_tool = MCPToolProxy(
            mcp_name="bigquery",
            tool_name="bigquery_query",
            tool_fn=bigquery_query_tool,
            mcp_schema={
                "description": "Execute SQL on BigQuery rx_claims table and save results to workspace",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "sql": {
                            "type": "string",
                            "description": "SQL query to execute"
                        },
                        "dataset_name": {
                            "type": "string",
                            "description": "Name for the output CSV file (without .csv extension)"
                        }
                    },
                    "required": ["sql", "dataset_name"]
                }
            },
            workspace_dir=str(workspace_dir)
        )

        agent.tools.register(bq_tool)

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break

            print("\n⏳ Processing...\n")
            print("Agent:")
            print("-" * 80)

            async for message in agent.run(user_input):
                if message.get("type") == "text_delta":
                    print(message["text"], end="", flush=True)
                elif message.get("type") == "tool_execution":
                    print(f"\n\n[Tool: {message['tool_name']}]", flush=True)

            print("\n" + "-" * 80)
            print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
