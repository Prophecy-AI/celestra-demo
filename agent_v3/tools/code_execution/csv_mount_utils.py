"""
Shared CSV mounting utilities for sandbox operations
"""
import polars as pl
from agent_v3.tools.logger import tool_log


def mount_single_csv(sandbox, dataset_name: str, local_csv_path: str, context) -> None:
    """
    Mount a single CSV file to the sandbox at /tmp/data/{dataset_name}.csv

    Args:
        sandbox: Modal Sandbox instance
        dataset_name: Name of the dataset (used for filename)
        local_csv_path: Path to local CSV file
        context: Context instance
    """
    try:
        # Read local file
        with open(local_csv_path, 'rb') as f:
            csv_data = f.read()

        # Extract schema using Polars
        df = pl.read_csv(local_csv_path)

        # Sanitize filename
        safe_name = dataset_name.replace('/', '_').replace(' ', '_')
        remote_path = f"/tmp/data/{safe_name}.csv"

        # Ensure /tmp/data exists
        mkdir_result = sandbox.exec("mkdir", "-p", "/tmp/data")
        mkdir_result.wait()

        # Write to sandbox
        with sandbox.open(remote_path, 'wb') as sf:
            sf.write(csv_data)

        tool_log("csv_mount", f"Mounted: {safe_name}.csv - {df.shape[0]:,} rows × {df.shape[1]} cols, {len(csv_data):,} bytes")
        tool_log("csv_mount", f"  Columns: {', '.join(df.columns[:10])}{'...' if len(df.columns) > 10 else ''}")

        # Inject schema information as system hint
        schema_hint = f"📊 NEW DATASET MOUNTED TO SANDBOX:\n\n"
        schema_hint += f"**{safe_name}.csv**: {df.shape[0]:,} rows × {df.shape[1]} columns\n"
        schema_hint += f"  Columns: {', '.join(df.columns)}\n"
        schema_hint += f"  Types: {', '.join([f'{col}:{str(dtype)}' for col, dtype in list(df.schema.items())[:5]])}{'...' if len(df.schema) > 5 else ''}\n"
        schema_hint += f"  Path: /tmp/data/{safe_name}.csv\n\n"
        schema_hint += "Use these exact column names when writing analysis code to avoid KeyError."

        context.add_system_hint(schema_hint)
        tool_log("csv_mount", f"Schema information for {safe_name}.csv injected into LLM context")

    except Exception as e:
        tool_log("csv_mount", f"Failed to mount {dataset_name}: {type(e).__name__}: {str(e)}", "error")
        raise


def mount_all_csvs(sandbox, context) -> None:
    """
    Mount all CSVs from context.csv_paths to sandbox at /tmp/data/

    Args:
        sandbox: Modal Sandbox instance
        context: Context instance with csv_paths populated
    """
    if not context.csv_paths:
        tool_log("csv_mount", "No CSVs to mount")
        return

    tool_log("csv_mount", f"Mounting {len(context.csv_paths)} CSV files to sandbox...")

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

            tool_log("csv_mount", f"Mounted: {safe_name}.csv - {df.shape[0]:,} rows × {df.shape[1]} cols, {len(csv_data):,} bytes")
            tool_log("csv_mount", f"  Columns: {', '.join(df.columns[:10])}{'...' if len(df.columns) > 10 else ''}")

        except Exception as e:
            tool_log("csv_mount", f"Failed to mount {dataset_name}: {type(e).__name__}: {str(e)}", "error")
            raise

    context.sandbox_mounted = True
    tool_log("csv_mount", f"CSV mounting complete: {len(context.csv_paths)} files ready")

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
        tool_log("csv_mount", "Schema information injected into LLM context for hallucination prevention")
