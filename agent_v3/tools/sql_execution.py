"""
SQL execution tool for BigQuery
"""
import os
import time
import polars as pl
from typing import Dict, Any, Optional
from google.cloud import bigquery
from google.cloud.exceptions import GoogleCloudError
from .base import Tool, ToolResult
from .logger import tool_log
from evals.retrieval_evaluator import evaluate_retrieval_relevancy


class BigQuerySQLQuery(Tool):
    """Execute SQL queries on BigQuery and return results as DataFrame"""

    def __init__(self):
        super().__init__(
            name="bigquery_sql_query",
            description="Execute SQL query on BigQuery and return results as DataFrame"
        )
        self.client = bigquery.Client(project=os.getenv("GCP_PROJECT"))
        self.timeout = 30.0  # 30 second timeout for queries

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Execute SQL query and return DataFrame with metadata"""
        error = self.validate_parameters(parameters, ["sql", "dataset_name"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        sql = parameters["sql"]
        dataset_name = parameters["dataset_name"]
        tool_log("bigquery_sql", f"Executing query for dataset: {dataset_name}")
        tool_log("bigquery_sql", f"SQL ({len(sql)} chars): {sql[:150]}...", "sql")

        try:
            # Validate SQL syntax basics
            validation_error = self._validate_sql(sql)
            if validation_error:
                tool_log("bigquery_sql", f"SQL validation failed: {validation_error}", "error")
                return ToolResult(success=False, data={}, error=validation_error)

            # Execute query
            start_time = time.time()
            tool_log("bigquery_sql", "Sending query to BigQuery...")
            query_job = self.client.query(sql)

            # Wait for query to complete with timeout
            try:
                results = query_job.result(timeout=self.timeout)
            except Exception as timeout_error:
                tool_log("bigquery_sql", f"Query timeout after {self.timeout}s", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error=f"Query timeout after {self.timeout}s: {str(timeout_error)}"
                )

            execution_time = time.time() - start_time
            tool_log("bigquery_sql", f"Query completed in {execution_time:.2f}s", "success")

            # Convert to Polars DataFrame
            arrow_table = results.to_arrow()
            df = pl.from_arrow(arrow_table)
            tool_log("bigquery_sql", f"Result shape: {df.shape[0]:,} rows × {df.shape[1]} columns")

            # Check for excessive size
            if df.shape[0] > 1_000_000:
                tool_log("bigquery_sql", f"Too many rows: {df.shape[0]:,}", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error=f"Query returned {df.shape[0]:,} rows (exceeds 1M row limit). Please add more filters."
                )

            # Detect sorting order
            sorting_desc = self._detect_sorting(df, sql)

            # Save to CSV
            csv_path = self._save_to_csv(df, dataset_name, context.session_id)
            if csv_path:
                tool_log("bigquery_sql", f"CSV saved: {csv_path}")

            # Store in context
            context.store_dataframe(dataset_name, df, sql, csv_path)

            # Prepare display (Polars handles truncation automatically)
            dataframe_display = str(df)
            tool_log("bigquery_sql", f"Dataset '{dataset_name}' ready with {len(df.columns)} columns", "success")

            # Evaluate retrieval relevancy
            try:
                user_query = getattr(context, 'original_user_query', 'User query not available')
                retrieval_eval = evaluate_retrieval_relevancy(user_query, df.to_dicts()[:100], sql)
                score = retrieval_eval.get('overall_relevancy', 'N/A')
                reasoning = retrieval_eval.get('reasoning', 'No reasoning provided')
                print(f"✅ Retrieval Evaluation: {score} - {reasoning}")
            except Exception as e:
                retrieval_eval = {"error": str(e)}
                print(f"⚠️ Retrieval evaluation failed: {e}")

            return ToolResult(
                success=True,
                data={
                    "dataframe_display": dataframe_display,
                    "shape": df.shape,
                    "columns": df.columns,  # Full list, no truncation
                    "sql_query": sql,
                    "dataset_name": dataset_name,
                    "csv_path": csv_path,
                    "sorting": sorting_desc,
                    "execution_time": execution_time,
                    "retrieval_evaluation": retrieval_eval
                }
            )

        except GoogleCloudError as e:
            tool_log("bigquery_sql", f"BigQuery error: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"BigQuery error: {str(e)}"
            )
        except Exception as e:
            tool_log("bigquery_sql", f"Unexpected error: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"Unexpected error: {str(e)}"
            )

    def _validate_sql(self, sql: str) -> Optional[str]:
        """Basic SQL validation"""
        sql_upper = sql.upper().strip()

        # Must start with SELECT or WITH
        if not sql_upper.startswith(('SELECT', 'WITH')):
            return "SQL must start with SELECT or WITH"

        # Check for dangerous operations
        dangerous_keywords = ['DELETE', 'DROP', 'INSERT', 'UPDATE', 'CREATE', 'ALTER', 'TRUNCATE']
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                return f"SQL contains forbidden operation: {keyword}"

        # Check for basic structure
        if 'SELECT' not in sql_upper:
            return "SQL must contain a SELECT statement"

        return None

    def _detect_sorting(self, df: pl.DataFrame, sql: str) -> str:
        """Detect the sorting order from SQL and data"""
        sql_upper = sql.upper()

        # Check SQL for ORDER BY
        if 'ORDER BY' in sql_upper:
            # Extract ORDER BY clause
            order_idx = sql_upper.find('ORDER BY')
            order_clause = sql[order_idx:].split('\n')[0]  # Get first line after ORDER BY

            # Check for DESC
            if 'DESC' in order_clause.upper():
                return f"Sorted in descending order by {self._extract_order_columns(order_clause)}"
            else:
                return f"Sorted in ascending order by {self._extract_order_columns(order_clause)}"

        # If no ORDER BY, check if results appear sorted by first column
        if len(df) > 1:
            first_col = df.columns[0]
            first_col_type = str(df[first_col].dtype)

            if 'Int' in first_col_type or 'Float' in first_col_type:
                # Check numeric sorting
                values = df[first_col].to_list()
                if values == sorted(values):
                    return f"Appears sorted ascending by {first_col}"
                elif values == sorted(values, reverse=True):
                    return f"Appears sorted descending by {first_col}"

        return "No explicit sorting applied"

    def _extract_order_columns(self, order_clause: str) -> str:
        """Extract column names from ORDER BY clause"""
        # Remove ORDER BY and DESC/ASC keywords
        cleaned = order_clause.replace('ORDER BY', '', 1)
        cleaned = cleaned.replace('DESC', '').replace('ASC', '')
        cleaned = cleaned.replace('LIMIT', ' LIMIT')  # Ensure LIMIT is separated

        # Split by LIMIT to remove any LIMIT clause
        if 'LIMIT' in cleaned:
            cleaned = cleaned.split('LIMIT')[0]

        # Clean up and return
        columns = cleaned.strip().strip(',')
        return columns if columns else "specified columns"

    def _save_to_csv(self, df: pl.DataFrame, dataset_name: str, session_id: str) -> str:
        """Save DataFrame to CSV file"""
        # Create output directory
        output_dir = f"output/session_{session_id}"
        os.makedirs(output_dir, exist_ok=True)

        # Generate filename (sanitize dataset name)
        safe_name = "".join(c if c.isalnum() or c in ('_', '-') else '_' for c in dataset_name)
        csv_path = os.path.join(output_dir, f"{safe_name}.csv")

        try:
            # Write CSV
            df.write_csv(csv_path)
            return csv_path
        except Exception as e:
            # If CSV write fails, return empty path but don't fail the tool
            print(f"Warning: Failed to save CSV: {str(e)}")
            return ""