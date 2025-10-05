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

        tool_log("sandbox_edit_file", f"Request to edit: {file_path}")
        tool_log("sandbox_edit_file", f"Replace: '{old_string[:50]}...' -> '{new_string[:50]}...'")

        # Validate sandbox exists
        if not context.sandbox:
            tool_log("sandbox_edit_file", "No sandbox exists - cannot edit file", "error")
            return ToolResult(
                success=False,
                data={},
                error="No sandbox exists. Use sandbox_write_file to create files first."
            )

        try:
            sandbox = context.sandbox
            tool_log("sandbox_edit_file", f"Reading file from sandbox {sandbox.object_id}")

            # Read file content
            result = sandbox.exec("cat", file_path)
            result.wait()

            if result.returncode != 0:
                error_msg = result.stderr.read() if result.stderr else "File not found"
                tool_log("sandbox_edit_file", f"Cannot read {file_path}: {error_msg}", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error=f"Cannot read file: {error_msg}"
                )

            content = result.stdout.read()
            tool_log("sandbox_edit_file", f"File content: {len(content)} bytes, {len(content.splitlines())} lines")

            # Count occurrences of old_string
            count = content.count(old_string)
            tool_log("sandbox_edit_file", f"Found {count} occurrence(s) of old_string")

            if count == 0:
                tool_log("sandbox_edit_file", f"old_string not found in {file_path}", "error")
                tool_log("sandbox_edit_file", f"File contains: {content[:200]}...", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error="old_string not found in file"
                )

            if count > 1:
                tool_log("sandbox_edit_file", f"old_string not unique: found {count} times", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error=f"old_string found {count} times - not unique. Include more context."
                )

            # Replace (exactly once)
            new_content = content.replace(old_string, new_string, 1)
            tool_log("sandbox_edit_file", f"Replacement complete, writing {len(new_content)} bytes back to file")

            # Write back
            with sandbox.open(file_path, 'w') as f:
                f.write(new_content)

            tool_log("sandbox_edit_file", f"Successfully edited {file_path}")

            return ToolResult(
                success=True,
                data={
                    "file_path": file_path
                }
            )

        except Exception as e:
            tool_log("sandbox_edit_file", f"Edit exception: {type(e).__name__}: {str(e)}", "error")
            tool_log("sandbox_edit_file", f"Failed file: {file_path}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"Edit failed: {str(e)}"
            )

    def get_success_hint(self, context: 'Context') -> Optional[str]:
        """Provide hint after successful edit (non-prescriptive)"""
        last_result = context.get_last_tool_result()
        file_path = last_result.get("file_path", "file")
        return f"File edited: {file_path}. Explore results or communicate with user about next steps."

    def get_error_hint(self, context: 'Context') -> Optional[str]:
        """Provide hint after edit error (non-prescriptive)"""
        last_result = context.get_last_tool_result()
        error = last_result.get("error", "")

        if "not unique" in error:
            return "Edit failed - old_string appeared multiple times. Consider viewing the file to identify unique context, or ask user for clarification."
        elif "not found" in error:
            return "Edit failed - old_string not found. Consider viewing file contents or asking user to verify the expected content."

        return "Edit operation failed. Consider viewing file contents or asking user for clarification on the intended change."
