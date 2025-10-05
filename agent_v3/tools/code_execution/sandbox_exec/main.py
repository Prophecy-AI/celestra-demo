"""
SandboxExec tool - Execute commands in Modal sandbox
"""
import os
import time
import modal
import polars as pl
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

        tool_log("sandbox_exec", f"Command: {' '.join(command)}, Timeout: {timeout}s")

        try:
            # Get or create sandbox
            sandbox = self._get_or_create_sandbox(context, timeout)

            # Execute command
            start_time = time.time()
            tool_log("sandbox_exec", f"Executing in sandbox {sandbox.object_id}")

            process = sandbox.exec(*command, timeout=timeout)
            process.wait()

            execution_time = time.time() - start_time

            # Capture stdout/stderr with truncation
            stdout = process.stdout.read()
            stderr = process.stderr.read()

            stdout_truncated = len(stdout) > self.max_stdout_size
            stderr_truncated = len(stderr) > self.max_stdout_size

            if stdout_truncated:
                tool_log("sandbox_exec", f"Stdout truncated: {len(stdout)} bytes -> {self.max_stdout_size} bytes", "warning")
                stdout = stdout[:self.max_stdout_size]
            if stderr_truncated:
                tool_log("sandbox_exec", f"Stderr truncated: {len(stderr)} bytes -> {self.max_stdout_size} bytes", "warning")
                stderr = stderr[:self.max_stdout_size]

            tool_log("sandbox_exec", f"Exit code: {process.returncode}, Duration: {execution_time:.2f}s")

            if process.returncode != 0:
                tool_log("sandbox_exec", f"Command failed with exit code {process.returncode}", "error")
                tool_log("sandbox_exec", f"Stderr: {stderr[:500]}", "error")

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
            tool_log("sandbox_exec", f"Sandbox execution exception: {type(e).__name__}: {str(e)}", "error")
            tool_log("sandbox_exec", f"Failed command: {' '.join(command)}", "error")
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
        """Copy all session CSVs to sandbox /tmp/data/ and extract schemas"""
        tool_log("sandbox_exec", f"Mounting {len(context.csv_paths)} CSV files to sandbox...")

        # Create directories
        mkdir_data = sandbox.exec("mkdir", "-p", "/tmp/data")
        mkdir_output = sandbox.exec("mkdir", "-p", "/tmp/output")
        mkdir_data.wait()
        mkdir_output.wait()

        # Extract schemas for anti-hallucination
        schemas = {}

        # Copy each CSV and extract schema
        for dataset_name, local_csv_path in context.csv_paths.items():
            try:
                # Read local file
                with open(local_csv_path, 'rb') as f:
                    csv_data = f.read()

                # Extract schema using Polars
                df = pl.read_csv(local_csv_path)
                schemas[dataset_name] = {
                    'shape': df.shape,
                    'columns': list(df.columns),
                    'dtypes': {col: str(dtype) for col, dtype in df.schema.items()}
                }

                # Sanitize filename
                safe_name = dataset_name.replace('/', '_').replace(' ', '_')
                remote_path = f"/tmp/data/{safe_name}.csv"

                # Write to sandbox
                with sandbox.open(remote_path, 'wb') as sf:
                    sf.write(csv_data)

                tool_log("sandbox_exec", f"Mounted: {safe_name}.csv - {df.shape[0]:,} rows × {df.shape[1]} cols, {len(csv_data):,} bytes")
                tool_log("sandbox_exec", f"  Columns: {', '.join(df.columns[:10])}{'...' if len(df.columns) > 10 else ''}")

            except Exception as e:
                tool_log("sandbox_exec", f"Failed to mount {dataset_name}: {type(e).__name__}: {str(e)}", "error")
                raise

        context.sandbox_mounted = True
        tool_log("sandbox_exec", f"CSV mounting complete: {len(context.csv_paths)} files ready")

        # Inject schema information as system hint (anti-hallucination)
        if schemas:
            schema_hint = "📊 AVAILABLE DATASETS IN SANDBOX:\n\n"
            for name, info in schemas.items():
                safe_name = name.replace('/', '_').replace(' ', '_')
                schema_hint += f"**{safe_name}.csv**: {info['shape'][0]:,} rows × {info['shape'][1]} columns\n"
                schema_hint += f"  Columns: {', '.join(info['columns'])}\n"
                schema_hint += f"  Types: {', '.join([f'{col}:{dtype}' for col, dtype in list(info['dtypes'].items())[:5]])}{'...' if len(info['dtypes']) > 5 else ''}\n"
                schema_hint += f"  Path: /tmp/data/{safe_name}.csv\n\n"

            schema_hint += "Use these exact column names when writing analysis code to avoid KeyError."

            context.add_system_hint(schema_hint)
            tool_log("sandbox_exec", "Schema information injected into LLM context for hallucination prevention")

    def _retrieve_output_files(self, sandbox: modal.Sandbox, context: 'Context') -> tuple[list[str], int]:
        """Copy sandbox output files to local session directory"""
        tool_log("sandbox_exec", "Scanning /tmp/output/ for files...")

        # List files in /tmp/output/
        result = sandbox.exec("find", "/tmp/output", "-type", "f")
        result.wait()

        if result.returncode != 0:
            tool_log("sandbox_exec", f"No output directory or find command failed (exit code {result.returncode})")
            return [], 0

        file_paths = result.stdout.read().strip().split('\n')
        output_files = []
        total_files = len([p for p in file_paths if p and p != '/tmp/output'])

        tool_log("sandbox_exec", f"Found {total_files} output files")

        # Process each file (max 20)
        for remote_path in file_paths[:self.max_output_files]:
            if not remote_path or remote_path == '/tmp/output':
                continue

            filename = remote_path.split('/')[-1]

            try:
                # Read from sandbox
                with sandbox.open(remote_path, 'rb') as sf:
                    content = sf.read()

                # Save locally
                session_dir = f"output/session_{context.session_id}"
                os.makedirs(session_dir, exist_ok=True)
                local_path = os.path.join(session_dir, filename)

                with open(local_path, 'wb') as lf:
                    lf.write(content)

                tool_log("sandbox_exec", f"Retrieved: {filename} ({len(content):,} bytes) -> {local_path}")

                # Handle visualizations
                if filename.endswith(('.png', '.jpg', '.svg', '.jpeg')):
                    io_handler = getattr(context, 'io_handler', None)
                    if io_handler and hasattr(io_handler, 'send_visualization'):
                        io_handler.send_visualization(local_path)
                        tool_log("sandbox_exec", f"Sent visualization to WebSocket: {filename}")

                output_files.append(filename)

            except Exception as e:
                tool_log("sandbox_exec", f"Failed to retrieve {filename}: {type(e).__name__}: {str(e)}", "error")

        if total_files > self.max_output_files:
            tool_log("sandbox_exec", f"Output file limit: retrieved {len(output_files)}/{total_files} files (max {self.max_output_files})", "warning")

        return output_files, total_files

    def get_success_hint(self, context: 'Context') -> Optional[str]:
        """Provide hint after successful execution (non-prescriptive)"""
        last_result = context.get_last_tool_result()

        if last_result.get("exit_code", 1) != 0:
            return "Execution failed. Review stderr to understand the issue. Consider asking user for clarification if error is unclear."

        output_files = last_result.get("output_files", [])
        if output_files:
            file_list = ', '.join(output_files[:5]) + ('...' if len(output_files) > 5 else '')
            return f"Code executed successfully. Output files: {file_list}. Explore results or communicate findings to user."
        else:
            return "Code executed successfully but no outputs in /tmp/output/. Consider asking user if results should be saved."
