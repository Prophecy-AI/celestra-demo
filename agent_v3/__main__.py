"""
Agent V3 entry points

Usage:
    python -m agent_v3              # Launch TUI
    python -m agent_v3 tui          # Launch TUI explicitly
    python -m agent_v3 main [args]  # Run agent with query
"""
import sys


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "main":
        # Run the main agent
        from agent_v3.main import main
        sys.argv.pop(1)  # Remove 'main' from args
        main()
    else:
        # Default: launch TUI
        from agent_v3.tui import main
        main()
