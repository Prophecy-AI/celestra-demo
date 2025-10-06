"""
BigQuery tool factory for Agent V5
Extracted from cli.py - this is the source of truth for BigQuery integration
"""
import polars as pl
from pathlib import Path
from google.cloud import bigquery
from google.oauth2.service_account import Credentials

from agent_v5.tools.mcp_proxy import MCPToolProxy


def create_bigquery_tool(
    workspace_dir: str,
    gcp_project: str,
    gcp_credentials: Credentials
) -> MCPToolProxy:
    """
    Create a BigQuery tool that executes SQL and saves results to workspace.

    Args:
        workspace_dir: Absolute path to workspace directory
        gcp_project: GCP project ID
        gcp_credentials: GCP service account credentials

    Returns:
        MCPToolProxy configured for BigQuery queries
    """
    workspace_path = Path(workspace_dir)

    async def bigquery_query_tool(args):
        """Execute SQL on BigQuery and save results to workspace"""
        client = bigquery.Client(project=gcp_project, credentials=gcp_credentials)
        query_job = client.query(args["sql"])
        results = query_job.result(timeout=30.0)

        arrow_table = results.to_arrow(create_bqstorage_client=False)
        df = pl.from_arrow(arrow_table)

        csv_path = workspace_path / f"{args['dataset_name']}.csv"
        df.write_csv(str(csv_path))

        preview = str(df.head(10))
        dataset_name = args['dataset_name']
        csv_absolute_path = str((workspace_path / f'{dataset_name}.csv').absolute())

        return {
            "content": [{
                "type": "text",
                "text": f"Saved {df.shape[0]:,} rows to {csv_absolute_path}\n\n{preview}"
            }]
        }

    bq_tool = MCPToolProxy(
        mcp_name="bigquery",
        tool_name="bigquery_query",
        tool_fn=bigquery_query_tool,
        mcp_schema={
            "description": "Execute SQL on BigQuery rx_claims table and save results to workspace",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "sql": {
                        "type": "string",
                        "description": "SQL query to execute"
                    },
                    "dataset_name": {
                        "type": "string",
                        "description": "Name for the output CSV file (without .csv extension)"
                    }
                },
                "required": ["sql", "dataset_name"]
            }
        },
        workspace_dir=workspace_dir
    )

    return bq_tool
