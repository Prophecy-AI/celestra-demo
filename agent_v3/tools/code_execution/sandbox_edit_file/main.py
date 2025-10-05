"""
SandboxEditFile tool - Edit files in Modal sandbox via exact string replacement
"""
from typing import Dict, Any, Optional, TYPE_CHECKING
from agent_v3.tools.base import Tool, ToolResult
from agent_v3.tools.categories import ToolCategory
from agent_v3.tools.logger import tool_log

if TYPE_CHECKING:
    from agent_v3.context import Context


class SandboxEditFile(Tool):
    """Modify existing files via exact string replacement"""

    def __init__(self):
        super().__init__(
            name="sandbox_edit_file",
            description="Modify files via exact string replacement",
            category=ToolCategory.FILE_MANAGEMENT
        )

    @classmethod
    def get_orchestrator_info(cls) -> str:
        """Return tool description for orchestrator system prompt"""
        return """- sandbox_edit_file: Modify files via exact string replacement
  Parameters: {"file_path": "/tmp/script.py", "old_string": "n=3", "new_string": "n=5"}
  Use when: Need to fix bugs or modify parameters in existing scripts"""

    def execute(self, parameters: Dict[str, Any], context: 'Context') -> ToolResult:
        """Edit file via exact string replacement"""
        error = self.validate_parameters(parameters, ["file_path", "old_string", "new_string"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        file_path = parameters["file_path"]
        old_string = parameters["old_string"]
        new_string = parameters["new_string"]

        tool_log("sandbox_edit_file", f"Editing: {file_path}")

        # Validate sandbox exists
        if not context.sandbox:
            return ToolResult(
                success=False,
                data={},
                error="No sandbox exists. Use sandbox_write_file to create files first."
            )

        try:
            sandbox = context.sandbox

            # Read file content
            result = sandbox.exec("cat", file_path)
            result.wait()

            if result.returncode != 0:
                error_msg = result.stderr.read() if result.stderr else "File not found"
                return ToolResult(
                    success=False,
                    data={},
                    error=f"Cannot read file: {error_msg}"
                )

            content = result.stdout.read()

            # Count occurrences of old_string
            count = content.count(old_string)

            if count == 0:
                return ToolResult(
                    success=False,
                    data={},
                    error="old_string not found in file"
                )

            if count > 1:
                return ToolResult(
                    success=False,
                    data={},
                    error=f"old_string found {count} times - not unique. Include more context."
                )

            # Replace (exactly once)
            new_content = content.replace(old_string, new_string, 1)

            # Write back
            with sandbox.open(file_path, 'w') as f:
                f.write(new_content)

            tool_log("sandbox_edit_file", "File edited successfully")

            return ToolResult(
                success=True,
                data={
                    "file_path": file_path
                }
            )

        except Exception as e:
            tool_log("sandbox_edit_file", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"Edit failed: {str(e)}"
            )

    def get_success_hint(self, context: 'Context') -> Optional[str]:
        """Provide hint after successful edit"""
        return "File edited successfully. Re-run with sandbox_exec."

    def get_error_hint(self, context: 'Context') -> Optional[str]:
        """Provide hint after edit error"""
        last_result = context.get_last_tool_result()
        error = last_result.get("error", "")

        if "not unique" in error:
            return "Edit failed - old_string not unique. Read file with sandbox_exec and include more surrounding context."
        elif "not found" in error:
            return "Edit failed - old_string not found. Read file first with sandbox_exec to see current content."

        return super().get_error_hint(context)
