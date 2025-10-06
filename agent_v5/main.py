"""
agent_v5: Modal sandbox function with ResearchAgent (no Claude Code SDK dependency)
"""
import modal
from typing import AsyncGenerator, Dict

app = modal.App("agent-v5")

image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ripgrep")
    .pip_install(
        "anthropic",
        "google-cloud-bigquery",
        "polars",
        "pyarrow",
        "numpy",
        "matplotlib",
        "scikit-learn"
    )
)

workspace_volume = modal.Volume.from_name("agent-workspaces", version=2, create_if_missing=True)

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
) -> AsyncGenerator[Dict, None]:
    import sys
    import json
    from pathlib import Path
    from google.oauth2 import service_account

    # Fix imports for Modal context
    sys.path.insert(0, "/root")

    from agent_v5.agent import ResearchAgent
    from agent_v5.tools.bigquery_tool import create_bigquery_tool

    creds_dict = json.loads(gcp_credentials_json)
    gcp_credentials = service_account.Credentials.from_service_account_info(creds_dict)

    session_dir = f"/workspace/{session_id}"
    Path(session_dir).mkdir(exist_ok=True, parents=True)

    agent = ResearchAgent(
        session_id=session_id,
        workspace_dir=session_dir,
        system_prompt=SYSTEM_PROMPT
    )

    bq_tool = create_bigquery_tool(
        workspace_dir=session_dir,
        gcp_project=gcp_project,
        gcp_credentials=gcp_credentials
    )

    agent.tools.register(bq_tool)

    async for message in agent.run(user_message):
        yield message

    workspace_volume.commit()


@app.local_entrypoint()
def chat():
    import os
    import uuid
    from dotenv import load_dotenv

    load_dotenv()

    GCP_PROJECT = os.getenv("GCP_PROJECT")
    GCP_CREDENTIALS_JSON = os.getenv("GCP_SERVICE_ACCOUNT_JSON")

    if not GCP_PROJECT or not GCP_CREDENTIALS_JSON:
        print("❌ Missing GCP_PROJECT or GCP_SERVICE_ACCOUNT_JSON in .env")
        return

    session_id = str(uuid.uuid4())[:8]

    print("=" * 80)
    print("🤖 Agent V5 - Research Engineer (No Claude Code SDK)")
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
            print("Agent:")
            print("-" * 80)

            for message in agent_turn.remote_gen(
                session_id=session_id,
                user_message=user_input,
                gcp_project=GCP_PROJECT,
                gcp_credentials_json=GCP_CREDENTIALS_JSON
            ):
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
