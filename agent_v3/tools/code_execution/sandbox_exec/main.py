"""
SandboxExec tool - Execute commands in Modal sandbox
"""
import os
import time
import modal
from typing import Dict, Any, Optional, TYPE_CHECKING
from agent_v3.tools.base import Tool, ToolResult
from agent_v3.tools.categories import ToolCategory
from agent_v3.tools.logger import tool_log

if TYPE_CHECKING:
    from agent_v3.context import Context


class SandboxExec(Tool):
    """Execute commands in isolated Modal sandbox"""

    def __init__(self):
        super().__init__(
            name="sandbox_exec",
            description="Execute commands in isolated Modal sandbox",
            category=ToolCategory.CODE_EXECUTION
        )
        self.max_stdout_size = 10 * 1024  # 10KB
        self.max_output_files = 20

    @classmethod
    def get_orchestrator_info(cls) -> str:
        """Return tool description for orchestrator system prompt"""
        return """- sandbox_exec: Execute commands in isolated Modal sandbox
  Parameters: {"command": ["python", "/tmp/script.py"], "timeout": 60}
  Use when: Need to run Python/bash commands for analysis, clustering, ML"""

    def execute(self, parameters: Dict[str, Any], context: 'Context') -> ToolResult:
        """Execute command in sandbox"""
        error = self.validate_parameters(parameters, ["command"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        command = parameters["command"]
        timeout = parameters.get("timeout", 60)

        # Validate timeout
        if timeout > 300:
            return ToolResult(success=False, data={}, error="Timeout max is 300 seconds")

        tool_log("sandbox_exec", f"Command: {' '.join(command)}")

        try:
            # Get or create sandbox
            sandbox = self._get_or_create_sandbox(context, timeout)

            # Execute command
            start_time = time.time()
            tool_log("sandbox_exec", "Executing command...")

            process = sandbox.exec(*command, timeout=timeout)
            process.wait()

            execution_time = time.time() - start_time

            # Capture stdout/stderr with truncation
            stdout = process.stdout.read()
            stderr = process.stderr.read()

            stdout_truncated = len(stdout) > self.max_stdout_size
            stderr_truncated = len(stderr) > self.max_stdout_size

            if stdout_truncated:
                stdout = stdout[:self.max_stdout_size]
            if stderr_truncated:
                stderr = stderr[:self.max_stdout_size]

            tool_log("sandbox_exec", f"Exit code: {process.returncode}, Time: {execution_time:.2f}s")

            # Retrieve output files
            output_files, total_files = self._retrieve_output_files(sandbox, context)

            if output_files:
                tool_log("sandbox_exec", f"Retrieved {len(output_files)} output files")

            return ToolResult(
                success=True,
                data={
                    "exit_code": process.returncode,
                    "stdout": stdout,
                    "stderr": stderr,
                    "stdout_truncated": stdout_truncated,
                    "stderr_truncated": stderr_truncated,
                    "output_files": output_files,
                    "total_output_files": total_files,
                    "execution_time": execution_time
                }
            )

        except Exception as e:
            tool_log("sandbox_exec", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"Sandbox execution failed: {str(e)}"
            )

    def _get_or_create_sandbox(self, context: 'Context', timeout: int) -> modal.Sandbox:
        """Get existing sandbox or create new one"""
        if context.sandbox:
            tool_log("sandbox_exec", "Using existing sandbox")
            return context.sandbox

        tool_log("sandbox_exec", "Creating new sandbox...")

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
            timeout=timeout,
            block_network=True,
            app=app
        )

        # Store in context
        context.sandbox = sandbox
        tool_log("sandbox_exec", f"Sandbox created: {sandbox.object_id}")

        # Mount CSVs if not already done
        if not context.sandbox_mounted:
            self._mount_csvs(sandbox, context)

        return sandbox

    def _mount_csvs(self, sandbox: modal.Sandbox, context: 'Context') -> None:
        """Copy all session CSVs to sandbox /tmp/data/"""
        tool_log("sandbox_exec", "Mounting CSVs to sandbox...")

        # Create directory
        sandbox.exec("mkdir", "-p", "/tmp/data").wait()
        sandbox.exec("mkdir", "-p", "/tmp/output").wait()

        # Copy each CSV
        for dataset_name, local_csv_path in context.csv_paths.items():
            # Read local file
            with open(local_csv_path, 'rb') as f:
                csv_data = f.read()

            # Sanitize filename
            safe_name = dataset_name.replace('/', '_').replace(' ', '_')
            remote_path = f"/tmp/data/{safe_name}.csv"

            # Write to sandbox
            with sandbox.open(remote_path, 'wb') as sf:
                sf.write(csv_data)

            tool_log("sandbox_exec", f"Mounted: {safe_name}.csv ({len(csv_data)} bytes)")

        context.sandbox_mounted = True
        tool_log("sandbox_exec", f"Mounted {len(context.csv_paths)} CSV files")

    def _retrieve_output_files(self, sandbox: modal.Sandbox, context: 'Context') -> tuple[list[str], int]:
        """Copy sandbox output files to local session directory"""

        # List files in /tmp/output/
        result = sandbox.exec("find", "/tmp/output", "-type", "f")
        result.wait()

        if result.returncode != 0:
            return [], 0

        file_paths = result.stdout.read().strip().split('\n')
        output_files = []
        total_files = len([p for p in file_paths if p and p != '/tmp/output'])

        # Process each file (max 20)
        for remote_path in file_paths[:self.max_output_files]:
            if not remote_path or remote_path == '/tmp/output':
                continue

            filename = remote_path.split('/')[-1]

            # Read from sandbox
            with sandbox.open(remote_path, 'rb') as sf:
                content = sf.read()

            # Save locally
            session_dir = f"output/session_{context.session_id}"
            os.makedirs(session_dir, exist_ok=True)
            local_path = os.path.join(session_dir, filename)

            with open(local_path, 'wb') as lf:
                lf.write(content)

            # Handle visualizations
            if filename.endswith(('.png', '.jpg', '.svg', '.jpeg')):
                io_handler = getattr(context, 'io_handler', None)
                if io_handler and hasattr(io_handler, 'send_visualization'):
                    io_handler.send_visualization(local_path)

            output_files.append(filename)

        return output_files, total_files

    def get_success_hint(self, context: 'Context') -> Optional[str]:
        """Provide hint after successful execution"""
        last_result = context.get_last_tool_result()

        if last_result.get("exit_code", 1) != 0:
            return "Execution failed. Review stderr and use sandbox_edit_file to fix errors."

        output_files = last_result.get("output_files", [])
        if output_files:
            return f"Code executed successfully. {len(output_files)} output file(s) created. Consider using 'complete' to present results."
        else:
            return "Code executed but no outputs in /tmp/output/. Verify script saves results."
