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

        # Use IOHandler if available, otherwise fallback to print/input
        io_handler = getattr(context, 'io_handler', None)

        # Display message to user
        output_msg = f"\n💬 Assistant: {message}"
        if io_handler:
            io_handler.send_output(output_msg)
        else:
            print(output_msg)

        # Get user response
        try:
            if io_handler:
                user_response = io_handler.get_user_input("\n👤 You: ").strip()
            else:
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

        # Use IOHandler if available
        io_handler = getattr(context, 'io_handler', None)

        # Helper function for output
        def output(msg: str):
            if io_handler:
                io_handler.send_output(msg)
            else:
                print(msg)

        # Display summary
        output("\n" + "="*80)
        output("📊 RESULTS SUMMARY")
        output("="*80)
        output(f"\n{summary}\n")

        # Display datasets if any
        if dataset_names:
            output("📁 DATASETS CREATED:")
            output("-"*40)

            for name in dataset_names:
                df = context.get_dataframe(name)
                if df is not None and not df.is_empty():
                    output(f"\n✅ {name}")
                    output(f"   Shape: {df.shape[0]:,} rows × {df.shape[1]} columns")

                    # Show column list
                    cols_msg = f"   Columns: {', '.join(df.columns[:5])}"
                    if len(df.columns) > 5:
                        cols_msg += f", ... ({len(df.columns)-5} more)"
                    output(cols_msg)

                    # Show CSV path if saved
                    csv_path = context.csv_paths.get(name)
                    if csv_path:
                        output(f"   💾 Saved to: {csv_path}")

                    # Show preview
                    output(f"\n   Preview:")
                    output("   " + "-"*36)

                    # Format dataframe display with indentation
                    df_display = str(df)
                    for line in df_display.split('\n'):
                        output(f"   {line}")

                    # Show SQL query (collapsible in real UI)
                    sql = context.queries.get(name)
                    if sql:
                        output(f"\n   SQL Query:")
                        output("   " + "-"*36)
                        # Show first 3 lines of SQL
                        sql_lines = sql.split('\n')
                        for i, line in enumerate(sql_lines[:3]):
                            output(f"   {line}")
                        if len(sql_lines) > 3:
                            output(f"   ... ({len(sql_lines)-3} more lines)")

            output("\n" + "="*80)

        # Get user feedback
        output("\n🤔 What would you like to do next?")
        output("   - Type your next request to continue analyzing")
        output("   - Type 'END' to finish the session")
        output("   - Press Enter to continue with current results")

        try:
            if io_handler:
                user_feedback = io_handler.get_user_input("\n👤 You: ").strip()
            else:
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