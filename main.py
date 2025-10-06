"""
agent_v5: Modal sandbox function with ResearchAgent (no Claude Code SDK dependency)
"""
import modal
from typing import AsyncGenerator, Dict
import json
from pathlib import Path
from google.oauth2 import service_account
import os
import uuid

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
        "seaborn",
        "matplotlib",
        "scikit-learn",
        "opentelemetry-api",
        "opentelemetry-sdk",
        "opentelemetry-instrumentation-anthropic",
        "langfuse"
    )
    .add_local_python_source("agent_v5")
    .add_local_python_source("bigquery_tool")
    .add_local_python_source("security")
    .add_local_python_source("observability")
)

workspace_volume = modal.Volume.from_name("agent-workspaces", version=2, create_if_missing=True)

SYSTEM_PROMPT = """You are a healthcare data research engineer with direct BigQuery access.

**Available Datasets:**

1. RX_CLAIMS (Prescription Data) - Table: `unique-bonbon-472921-q8.Claims.rx_claims`
   - PRESCRIBER_NPI_NBR: Prescriber's NPI
   - NDC_DRUG_NM: Drug name
   - NDC_PREFERRED_BRAND_NM: Brand name
   - PRESCRIBER_NPI_STATE_CD: State
   - SERVICE_DATE_DD: Fill date
   - DISPENSED_QUANTITY_VAL: Quantity

2. MED_CLAIMS (Medical Claims) - Table: `unique-bonbon-472921-q8.Claims.medical_claims`
   - PRIMARY_HCP: Provider identifier
   - condition_label: Diagnosis/condition
   - PROCEDURE_CD: Procedure code
   - RENDERING_PROVIDER_STATE: State
   - STATEMENT_FROM_DD: Service date
   - CLAIM_CHARGE_AMT: Charge amount

3. PROVIDER_PAYMENTS (Healthcare Providers Payments) - Table: `unique-bonbon-472921-q8.HCP.provider_payments`
   - npi_number: National Provider Identifier
   - associated_product: Associated product
   - nature_of_payment: Nature of payment
   - payer_company: Payer company
   - product_type: Product type
   - program_year: Program year
   - record_id: Record ID
   - total_payment_amount: Total payment amount

4. PROVIDERS_BIO (Healthcare Providers Biographical) - Table: `unique-bonbon-472921-q8.HCP.providers_bio`
   - npi_number: National Provider Identifier
   - title: Professional title
   - specialty: Medical specialty
   - certifications: Certifications held by the provider
   - education: Educational background of the provider
   - awards: Awards received by the provider
   - memberships: Professional memberships of the provider
   - conditions_treated: Conditions treated by the provider

**Your Tools:**
- mcp__bigquery__bigquery_query: Execute SQL queries on all 4 tables and save results to CSV in workspace
- Read: Read files from workspace
- Write: Create files and Python scripts
- Edit: Modify existing files
- Bash: Execute shell commands and run Python scripts
- Glob: Find files by pattern
- Grep: Search file contents

**Research Workflow:**
1. Understand the research question
2. Query BigQuery for relevant data (can join across tables)
3. Analyze with Python/Polars if needed
4. Present findings clearly

**Guidelines:**
- Use plain English when explaining results
- Suggest follow-up analyses proactively
- Save intermediate results as CSV files
- Create visualizations when helpful
- Join tables when richer insights are needed (e.g., prescription + provider bio)

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
    from agent_v5.agent import ResearchAgent
    from bigquery_tool import create_bigquery_tool
    from security import create_path_validation_prehook
    from observability import otel, langfuse_client

    # Setup observability (only active if env vars set)
    otel.setup()
    langfuse_client.setup()

    creds_dict = json.loads(gcp_credentials_json)
    gcp_credentials = service_account.Credentials.from_service_account_info(creds_dict)

    session_dir = f"/workspace/{session_id}"
    Path(session_dir).mkdir(exist_ok=True, parents=True)

    agent = ResearchAgent(
        session_id=session_id,
        workspace_dir=session_dir,
        system_prompt=SYSTEM_PROMPT
    )

    # Inject security prehooks for filesystem tools
    path_hook = create_path_validation_prehook(session_dir)
    agent.tools.set_prehook("Read", path_hook)
    agent.tools.set_prehook("Write", path_hook)
    agent.tools.set_prehook("Edit", path_hook)
    agent.tools.set_prehook("Glob", path_hook)
    agent.tools.set_prehook("Grep", path_hook)

    bq_tool = create_bigquery_tool(
        workspace_dir=session_dir,
        gcp_project=gcp_project,
        gcp_credentials=gcp_credentials
    )

    agent.tools.register(bq_tool)

    async for message in agent.run(user_message):
        yield message

    workspace_volume.commit()


@app.function(
    image=image,
    volumes={"/workspace": workspace_volume},
    timeout=60,
)
def list_session_files(session_id: str) -> Dict:
    """List all files in a session directory"""
    session_dir = Path(f"/workspace/{session_id}")

    if not session_dir.exists():
        return {"error": f"Session {session_id} not found"}

    files = []
    for path in session_dir.rglob("*"):
        if path.is_file():
            rel_path = path.relative_to(session_dir)
            files.append({
                "path": str(rel_path),
                "size": path.stat().st_size,
                "modified": path.stat().st_mtime
            })

    return {"session_id": session_id, "files": files}


@app.function(
    image=image,
    volumes={"/workspace": workspace_volume},
    timeout=60,
)
def download_file(session_id: str, file_path: str) -> Dict:
    """Download a specific file from session directory"""
    session_dir = Path(f"/workspace/{session_id}")
    target_file = session_dir / file_path

    if not target_file.exists() or not target_file.is_file():
        return {"error": f"File not found: {file_path}"}

    # Ensure file is within session directory (security check)
    if not str(target_file.resolve()).startswith(str(session_dir.resolve())):
        return {"error": "Access denied: file outside session directory"}

    content = target_file.read_bytes()

    return {
        "session_id": session_id,
        "file_path": file_path,
        "content": content,
        "size": len(content)
    }


@app.local_entrypoint()
def chat():
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
    print("Type 'exit' to quit, '/download' to download all files")
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

            # Handle download command
            if user_input.lower() == '/download':
                print("\n📥 Downloading files from Modal workspace...")
                try:
                    result = list_session_files.remote(session_id)

                    if "error" in result:
                        print(f"❌ {result['error']}")
                        continue

                    files = result["files"]
                    if not files:
                        print("ℹ️  No files found in workspace")
                        continue

                    print(f"Found {len(files)} file(s):")
                    for f in files:
                        print(f"  - {f['path']} ({f['size']:,} bytes)")

                    # Download to local directory
                    download_dir = Path(f"./downloads/{session_id}")
                    download_dir.mkdir(parents=True, exist_ok=True)

                    for file_info in files:
                        file_path = file_info['path']
                        print(f"\n  Downloading {file_path}...", end="", flush=True)

                        file_result = download_file.remote(session_id, file_path)

                        if "error" in file_result:
                            print(f" ❌ {file_result['error']}")
                            continue

                        local_path = download_dir / file_path
                        local_path.parent.mkdir(parents=True, exist_ok=True)
                        local_path.write_bytes(file_result["content"])

                        print(f" ✅")

                    print(f"\n✅ Downloaded {len(files)} file(s) to {download_dir.absolute()}\n")

                except Exception as e:
                    print(f"❌ Download failed: {str(e)}\n")

                continue

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
