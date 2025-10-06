"""
agent_v4: Modal sandbox function for Claude Code agent with BigQuery
"""
import modal
from typing import List, Dict

app = modal.App("agent-v4")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("nodejs", "npm")
    .run_commands("npm install -g @anthropic-ai/claude-code")
    .pip_install(
        "claude-agent-sdk",
        "google-cloud-bigquery",
        "polars",
        "pyarrow",
        "numpy",
        "matplotlib",
        "scikit-learn"
    )
)

# Shared volume with per-session isolation via subdirectories
workspace_volume = modal.Volume.from_name("agent-workspaces", version=2, create_if_missing=True)

SYSTEM_PROMPT = """You are a healthcare data analyst with direct BigQuery access.

**Available Dataset:**

RX_CLAIMS - Table: `unique-bonbon-472921-q8.Claims.rx_claims`
- PRESCRIBER_NPI_NBR: Prescriber NPI
- NDC_DRUG_NM: Drug name
- NDC_PREFERRED_BRAND_NM: Brand name
- PRESCRIBER_NPI_STATE_CD: State
- SERVICE_DATE_DD: Fill date
- DISPENSED_QUANTITY_VAL: Quantity

**Tools:**
- bigquery_query: Execute SQL, saves CSV to /workspace
- Read: Read files
- Write: Create Python scripts
- Bash: Execute commands

**Workflow:**
1. Query BigQuery for data
2. Analyze with Python/Polars
3. Present findings

Current date: 2025-10-05"""


@app.function(
    image=image,
    secrets=[modal.Secret.from_dotenv()],
    volumes={"/workspace": workspace_volume},
    timeout=600,
    min_containers=1,
)
async def agent_turn(
    session_id: str,
    user_message: str,
    gcp_project: str,
    gcp_credentials_json: str
):
    import json
    import polars as pl
    from pathlib import Path
    from google.oauth2 import service_account
    from claude_agent_sdk import (
        ClaudeSDKClient,
        ClaudeAgentOptions,
        tool,
        create_sdk_mcp_server
    )

    # Setup GCP credentials (memory only, never written to disk)
    creds_dict = json.loads(gcp_credentials_json)
    gcp_credentials = service_account.Credentials.from_service_account_info(creds_dict)

    # Session-specific workspace
    session_dir = f"/workspace/{session_id}"
    Path(session_dir).mkdir(exist_ok=True, parents=True)

    @tool(
        "bigquery_query",
        "Execute SQL on BigQuery rx_claims table and save results to /workspace",
        {"sql": str, "dataset_name": str}
    )
    async def bigquery_query(args):
        from google.cloud import bigquery
        client = bigquery.Client(project=gcp_project, credentials=gcp_credentials)
        query_job = client.query(args["sql"])
        results = query_job.result(timeout=30.0)

        arrow_table = results.to_arrow(create_bqstorage_client=False)
        df = pl.from_arrow(arrow_table)

        csv_path = f"{session_dir}/{args['dataset_name']}.csv"
        df.write_csv(csv_path)

        preview = str(df.head(10))
        return {
            "content": [{
                "type": "text",
                "text": f"Saved {df.shape[0]:,} rows to {args['dataset_name']}.csv\n\n{preview}"
            }]
        }

    bq_server = create_sdk_mcp_server(
        name="bigquery",
        version="1.0.0",
        tools=[bigquery_query]
    )

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_PROMPT,
        allowed_tools=["Read", "Write", "Bash", "mcp__bigquery__bigquery_query"],
        mcp_servers={"bigquery": bq_server},
        cwd=session_dir,
        permission_mode="acceptEdits",
        max_turns=20
    )

    async with ClaudeSDKClient(options=options) as client:
        await client.query(user_message)

        async for message in client.receive_response():
            yield str(message)

    workspace_volume.commit()


@app.local_entrypoint()
def chat():
    import os
    import uuid
    from dotenv import load_dotenv

    load_dotenv()

    # Load credentials from local .env
    GCP_PROJECT = os.getenv("GCP_PROJECT")
    GCP_CREDENTIALS_JSON = os.getenv("GCP_SERVICE_ACCOUNT_JSON")

    if not GCP_PROJECT or not GCP_CREDENTIALS_JSON:
        print("❌ Missing GCP_PROJECT or GCP_SERVICE_ACCOUNT_JSON in .env")
        return

    # Generate session ID
    session_id = str(uuid.uuid4())[:8]

    print("=" * 80)
    print("🤖 Agent V4 - Interactive Research Assistant")
    print("=" * 80)
    print(f"Session: {session_id}")
    print(f"Workspace: /workspace/{session_id}/ (persists across messages)")
    print("Type 'exit' to quit")
    print("=" * 80)
    print()

    while True:
        try:
            user_input = input("You: ").strip()

            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit', 'q']:
                print("\n👋 Goodbye!")
                break

            print("\n⏳ Processing...\n")

            # Stream messages in real-time from Modal function
            for message in agent_turn.remote_gen(
                session_id=session_id,
                user_message=user_input,
                gcp_project=GCP_PROJECT,
                gcp_credentials_json=GCP_CREDENTIALS_JSON
            ):
                print(message)
                print("-" * 80)

            print()

        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}\n")
