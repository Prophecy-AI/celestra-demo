"""
Local interactive REPL for agent_v4
Credentials stay on your machine, passed as encrypted parameters to Modal
"""
import os
import uuid
from dotenv import load_dotenv
from agent_v4.main import agent_turn

load_dotenv()

# Load credentials from local .env
GCP_PROJECT = os.getenv("GCP_PROJECT")
GCP_CREDENTIALS_JSON = os.getenv("GCP_SERVICE_ACCOUNT_JSON")

if not GCP_PROJECT or not GCP_CREDENTIALS_JSON:
    print("❌ Missing GCP_PROJECT or GCP_SERVICE_ACCOUNT_JSON in .env")
    exit(1)

# Generate session ID
session_id = str(uuid.uuid4())[:8]

print("=" * 80)
print("🤖 Agent V4 - Interactive Research Assistant")
print("=" * 80)
print(f"Session: {session_id}")
print("Workspace: /workspace/{session_id}/ (persists across messages)")
print("Type 'exit' to quit")
print("=" * 80)
print()

while True:
        user_input = input("You: ").strip()

        if not user_input:
            continue

        if user_input.lower() in ['exit', 'quit', 'q']:
            print("\n👋 Goodbye!")
            break

        print("\n⏳ Processing...\n")

        # Call Modal function with credentials as parameters
        response = agent_turn.remote(
            session_id=session_id,
            user_message=user_input,
            gcp_project=GCP_PROJECT,
            gcp_credentials_json=GCP_CREDENTIALS_JSON
        )

        print("Agent:")
        print("-" * 80)
        print(response)
        print("-" * 80)
        print()

    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        break
    except Exception as e:
        print(f"\n❌ Error: {str(e)}\n")
