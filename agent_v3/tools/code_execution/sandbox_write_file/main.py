"""
SandboxWriteFile tool - Write files to Modal sandbox
"""
import modal
from typing import Dict, Any, Optional, TYPE_CHECKING
from agent_v3.tools.base import Tool, ToolResult
from agent_v3.tools.categories import ToolCategory
from agent_v3.tools.logger import tool_log

if TYPE_CHECKING:
    from agent_v3.context import Context


class SandboxWriteFile(Tool):
    """Create or overwrite files in sandbox"""

    def __init__(self):
        super().__init__(
            name="sandbox_write_file",
            description="Create or overwrite files in sandbox",
            category=ToolCategory.FILE_MANAGEMENT
        )
        self.max_content_size = 5 * 1024 * 1024  # 5MB

    @classmethod
    def get_orchestrator_info(cls) -> str:
        """Return tool description for orchestrator system prompt"""
        return """- sandbox_write_file: Create or overwrite files in sandbox
  Parameters: {"file_path": "/tmp/script.py", "content": "import polars as pl..."}
  Use when: Need to create Python scripts for analysis"""

    def execute(self, parameters: Dict[str, Any], context: 'Context') -> ToolResult:
        """Write content to file in sandbox"""
        error = self.validate_parameters(parameters, ["file_path", "content"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        file_path = parameters["file_path"]
        content = parameters["content"]

        tool_log("sandbox_write_file", f"Writing to: {file_path}")

        # Validate path
        if not (file_path.startswith('/tmp/') or file_path.startswith('/workspace/')):
            return ToolResult(
                success=False,
                data={},
                error="Invalid path: must be /tmp/* or /workspace/*"
            )

        # Validate content size
        content_bytes = content.encode('utf-8')
        if len(content_bytes) > self.max_content_size:
            return ToolResult(
                success=False,
                data={},
                error=f"Content too large: {len(content_bytes)} bytes (max {self.max_content_size})"
            )

        try:
            # Ensure sandbox exists
            sandbox = self._ensure_sandbox(context)

            # Write file
            with sandbox.open(file_path, 'w') as f:
                f.write(content)

            bytes_written = len(content_bytes)
            tool_log("sandbox_write_file", f"Wrote {bytes_written} bytes")

            return ToolResult(
                success=True,
                data={
                    "file_path": file_path,
                    "bytes_written": bytes_written
                }
            )

        except Exception as e:
            tool_log("sandbox_write_file", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"Write failed: {str(e)}"
            )

    def _ensure_sandbox(self, context: 'Context') -> modal.Sandbox:
        """Ensure sandbox exists, create if needed"""
        if context.sandbox:
            return context.sandbox

        tool_log("sandbox_write_file", "Creating sandbox...")

        # Get or create Modal app
        app = modal.App.lookup("agent-sandbox", create_if_missing=True)

        # Create sandbox image
        image = modal.Image.debian_slim(python_version="3.11").pip_install(
            "polars",
            "numpy",
            "matplotlib",
            "seaborn",
            "scikit-learn"
        )

        # Create sandbox
        sandbox = modal.Sandbox.create(
            image=image,
            timeout=60,
            block_network=True,
            app=app
        )

        # Store in context
        context.sandbox = sandbox
        tool_log("sandbox_write_file", f"Sandbox created: {sandbox.object_id}")

        # Create output directory
        sandbox.exec("mkdir", "-p", "/tmp/output").wait()

        return sandbox

    def get_success_hint(self, context: 'Context') -> Optional[str]:
        """Provide hint after successful write"""
        return "File written successfully. Use sandbox_exec to run it."
