"""
Main entry point for agent_v3
"""
import os
import sys
import time
import argparse
from datetime import datetime
from dotenv import load_dotenv
from .orchestrator import RecursiveOrchestrator
from langfuse import Langfuse, observe, get_client

load_dotenv()
langfuse = Langfuse(
  secret_key=os.getenv("LANGFUSE_SECRET"),
  public_key=os.getenv("LANGFUSE_PUBLIC"),
  host="https://us.cloud.langfuse.com"
)
langfuse = get_client()

def validate_environment():
    """Validate required environment variables"""
    load_dotenv()

    required_vars = ["ANTHROPIC_API_KEY", "GCP_PROJECT"]
    missing = []

    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        print(f"❌ Missing required environment variables: {', '.join(missing)}")
        print("Please set them in your .env file")
        sys.exit(1)

    print("✅ Environment validated")


def print_banner():
    """Print welcome banner"""
    print("\n" + "="*80)
    print("🚀 HEALTHCARE DATA ANALYSIS AGENT v3.0")
    print("="*80)
    print("Recursive orchestration with single-tool execution")
    print("Using Claude Sonnet 4 (2025-05-14)")
    print("-"*80)


def run_interactive(debug: bool = False):
    """Run the agent in interactive mode"""
    validate_environment()
    print_banner()

    print("\n💡 Tips:")
    print("  - Ask for prescribers of specific drugs")
    print("  - Query providers treating certain conditions")
    print("  - Combine multiple criteria for targeted lists")
    print("  - Type 'quit' or 'exit' to end the session")
    print("-"*80)

    while True:
        try:
            # Get user input
            user_input = input("\n👤 You: ").strip()

            # Check for exit commands
            if user_input.lower() in ['quit', 'exit', 'bye']:
                print("\n👋 Thank you for using Healthcare Data Analysis Agent!")
                break

            if not user_input:
                continue

            # Create session ID
            session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

            # Initialize orchestrator
            print("\n🔄 Processing your request...\n")
            orchestrator = RecursiveOrchestrator(session_id, debug=debug)

            # Run the orchestration
            start_time = time.time()
            result = orchestrator.run(user_input)
            duration = time.time() - start_time

            # Display results summary
            if result.get("success"):
                print("\n" + "="*80)
                print("✅ SESSION COMPLETED SUCCESSFULLY")
                print("="*80)
                summary = result.get("summary", {})
                print(f"📊 Datasets created: {summary.get('datasets_created', 0)}")
                print(f"🔧 Tools executed: {summary.get('total_tools_executed', 0)}")
                print(f"📈 Total rows collected: {summary.get('total_rows', 0):,}")
                print(f"⏱️  Duration: {duration:.1f} seconds")
                print(f"💾 Session ID: {session_id}")
            else:
                print("\n" + "="*80)
                print("⚠️  SESSION ENDED WITH ISSUES")
                print("="*80)
                if result.get("error"):
                    print(f"Error: {result['error']}")

        except KeyboardInterrupt:
            print("\n\n🛑 Interrupted by user")
            break
        except Exception as e:
            print(f"\n❌ Unexpected error: {str(e)}")
            if debug:
                import traceback
                traceback.print_exc()

def run_single_query(query: str, debug: bool = False):
    """Run a single query and exit"""
    validate_environment()

    # Create session ID
    session_id = datetime.now().strftime("%Y%m%d_%H%M%S")

    print(f"\n🔄 Processing query: {query}\n")

    # Initialize orchestrator
    orchestrator = RecursiveOrchestrator(session_id, debug=debug)

    # Run the orchestration
    start_time = time.time()
    result = orchestrator.run(query)
    duration = time.time() - start_time

    # Display results
    if result.get("success"):
        print("\n✅ Query completed successfully")
        summary = result.get("summary", {})
        print(f"📊 Datasets: {', '.join(summary.get('dataset_names', []))}")
        print(f"⏱️  Duration: {duration:.1f}s")
    else:
        print(f"\n❌ Query failed: {result.get('error', 'Unknown error')}")

@observe
def main():
    """Main entry point with CLI argument parsing"""
    parser = argparse.ArgumentParser(
        description="Healthcare Data Analysis Agent v3.0",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python -m agent_v3.main
      Run in interactive mode

  python -m agent_v3.main --query "Find prescribers of HUMIRA in California"
      Run a single query

  python -m agent_v3.main --debug
      Run with debug logging enabled
        """
    )

    parser.add_argument(
        "--query", "-q",
        type=str,
        help="Run a single query and exit"
    )

    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug logging"
    )

    args = parser.parse_args()

    if args.query:
        run_single_query(args.query, debug=args.debug)
    else:
        run_interactive(debug=args.debug)


if __name__ == "__main__":
    main()