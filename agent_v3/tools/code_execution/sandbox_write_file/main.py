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

        tool_log("sandbox_write_file", f"Request to write: {file_path}")

        # Validate path
        if not (file_path.startswith('/tmp/') or file_path.startswith('/workspace/')):
            tool_log("sandbox_write_file", f"Path validation failed: {file_path} (must be /tmp/* or /workspace/*)", "error")
            return ToolResult(
                success=False,
                data={},
                error="Invalid path: must be /tmp/* or /workspace/*"
            )

        # Validate content size
        content_bytes = content.encode('utf-8')
        if len(content_bytes) > self.max_content_size:
            tool_log("sandbox_write_file", f"Content too large: {len(content_bytes)} bytes (max {self.max_content_size})", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"Content too large: {len(content_bytes)} bytes (max {self.max_content_size})"
            )

        tool_log("sandbox_write_file", f"Content size: {len(content_bytes):,} bytes, {len(content.splitlines())} lines")

        try:
            # Ensure sandbox exists
            sandbox = self._ensure_sandbox(context)
            tool_log("sandbox_write_file", f"Writing to sandbox {sandbox.object_id}")

            # Write file
            with sandbox.open(file_path, 'w') as f:
                f.write(content)

            bytes_written = len(content_bytes)
            tool_log("sandbox_write_file", f"Successfully wrote {bytes_written:,} bytes to {file_path}")

            return ToolResult(
                success=True,
                data={
                    "file_path": file_path,
                    "bytes_written": bytes_written
                }
            )

        except Exception as e:
            tool_log("sandbox_write_file", f"Write exception: {type(e).__name__}: {str(e)}", "error")
            tool_log("sandbox_write_file", f"Failed path: {file_path}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"Write failed: {str(e)}"
            )

    def _ensure_sandbox(self, context: 'Context') -> modal.Sandbox:
        """Ensure sandbox exists, create if needed"""
        if context.sandbox:
            tool_log("sandbox_write_file", f"Using existing sandbox {context.sandbox.object_id}")
            return context.sandbox

        tool_log("sandbox_write_file", "No sandbox exists, creating new one...")

        try:
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
                timeout=24 * 60 * 60, # 24 hours
                idle_timeout=60, # 60 seconds
                block_network=True,
                app=app
            )

            # Store in context
            context.sandbox = sandbox
            tool_log("sandbox_write_file", f"Sandbox created successfully: {sandbox.object_id}")

            # Create output directory
            mkdir_result = sandbox.exec("mkdir", "-p", "/tmp/output")
            mkdir_result.wait()
            tool_log("sandbox_write_file", "Output directory /tmp/output/ created")

            return sandbox

        except Exception as e:
            tool_log("sandbox_write_file", f"Sandbox creation failed: {type(e).__name__}: {str(e)}", "error")
            raise

    def get_success_hint(self, context: 'Context') -> Optional[str]:
        """Provide hint after successful write (non-prescriptive)"""
        last_result = context.get_last_tool_result()
        file_path = last_result.get("file_path", "file")

        # Get list of available datasets for context
        dataset_count = len(context.csv_paths)
        dataset_hint = f"{dataset_count} dataset(s) available in /tmp/data/" if dataset_count > 0 else "No datasets mounted yet"

        return f"File written: {file_path}. {dataset_hint}. Consider exploring data or asking user for clarification if approach is unclear."
