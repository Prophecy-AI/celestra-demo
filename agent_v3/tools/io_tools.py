"""
I/O tools for user communication and completion
"""
from typing import Dict, Any, List
from .base import Tool, ToolResult


class Communicate(Tool):
    """Tool for communicating with the user"""

    def __init__(self):
        super().__init__(
            name="communicate",
            description="Ask user for clarification or provide intermediate updates"
        )

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Send message to user and get response"""
        error = self.validate_parameters(parameters, ["message"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        message = parameters["message"]

        # Display message to user
        print(f"\n💬 Assistant: {message}")

        # Get user response
        try:
            user_response = input("\n👤 You: ").strip()

            return ToolResult(
                success=True,
                data={
                    "user_response": user_response
                }
            )
        except (KeyboardInterrupt, EOFError):
            return ToolResult(
                success=False,
                data={},
                error="User input interrupted"
            )


class Complete(Tool):
    """Tool for presenting final results and getting feedback"""

    def __init__(self):
        super().__init__(
            name="complete",
            description="Present final results and datasets to user"
        )

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Present results and get user feedback"""
        error = self.validate_parameters(parameters, ["summary", "datasets"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        summary = parameters["summary"]
        dataset_names = parameters["datasets"]

        # Display summary
        print("\n" + "="*80)
        print("📊 RESULTS SUMMARY")
        print("="*80)
        print(f"\n{summary}\n")

        # Display datasets if any
        if dataset_names:
            print("📁 DATASETS CREATED:")
            print("-"*40)

            for name in dataset_names:
                df = context.get_dataframe(name)
                if df is not None:
                    print(f"\n✅ {name}")
                    print(f"   Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")

                    # Show column list
                    print(f"   Columns: {', '.join(df.columns[:5])}", end="")
                    if len(df.columns) > 5:
                        print(f", ... ({len(df.columns)-5} more)")
                    else:
                        print()

                    # Show CSV path if saved
                    csv_path = context.csv_paths.get(name)
                    if csv_path:
                        print(f"   💾 Saved to: {csv_path}")

                    # Show preview
                    print(f"\n   Preview:")
                    print("   " + "-"*36)

                    # Format dataframe display with indentation
                    df_display = str(df)
                    for line in df_display.split('\n'):
                        print(f"   {line}")

                    # Show SQL query (collapsible in real UI)
                    sql = context.queries.get(name)
                    if sql:
                        print(f"\n   SQL Query:")
                        print("   " + "-"*36)
                        # Show first 3 lines of SQL
                        sql_lines = sql.split('\n')
                        for i, line in enumerate(sql_lines[:3]):
                            print(f"   {line}")
                        if len(sql_lines) > 3:
                            print(f"   ... ({len(sql_lines)-3} more lines)")

            print("\n" + "="*80)

        # Get user feedback
        print("\n🤔 What would you like to do next?")
        print("   - Type your next request to continue analyzing")
        print("   - Type 'END' to finish the session")
        print("   - Press Enter to continue with current results")

        try:
            user_feedback = input("\n👤 You: ").strip()

            # Parse action
            action = "end" if user_feedback.upper() == "END" else "continue"

            # If user just pressed Enter, provide a default continue message
            if not user_feedback and action == "continue":
                user_feedback = "Continue with the current analysis"

            return ToolResult(
                success=True,
                data={
                    "feedback": user_feedback,
                    "action": action
                }
            )

        except (KeyboardInterrupt, EOFError):
            return ToolResult(
                success=True,
                data={
                    "feedback": "Session interrupted by user",
                    "action": "end"
                }
            )