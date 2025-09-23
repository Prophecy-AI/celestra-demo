"""
Medical Claims Agent - handles medical claims queries
"""
import os
import sys
import time
import polars as pl
from typing import Union, Dict, Any
from google.cloud import bigquery
from dotenv import load_dotenv
import anthropic
from .context import SharedContext, TaskStatus

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.med_claims_prompt import SYSTEM_PROMPT as MED_CLAIMS_PROMPT

load_dotenv()

class MedClaimsAgent:
    def __init__(self, context: SharedContext):
        self.context = context
        self.bq_client = bigquery.Client(project=os.getenv("GCP_PROJECT"))
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # Dataset is hardcoded in the med_claims_prompt.py already
        self.debug = os.getenv('DEBUG', '0') == '1'

    def log(self, message: str):
        """Debug logging"""
        if self.debug:
            print(f"[MED-AGENT][{time.strftime('%H:%M:%S')}] {message}")

    def generate_sql(self, request: str) -> str:
        """Generate SQL query from natural language request"""
        self.log(f"[SQL-GEN] Generating SQL for request: {request}")
        self.log(f"[SQL-GEN] Using system prompt of length: {len(MED_CLAIMS_PROMPT)}")

        response = self.anthropic_client.messages.create(
            model="claude-3-haiku-20240307",
            max_tokens=1024,
            system=MED_CLAIMS_PROMPT,
            messages=[{"role": "user", "content": request}],
            temperature=0
        )

        sql = response.content[0].text.strip()
        sql = sql.replace("```sql", "").replace("```", "").strip()

        self.log(f"[SQL-GEN] Generated SQL: {sql}")
        return sql

    def execute(self, task_id: str, request: str) -> Union[pl.DataFrame, str]:
        """Execute medical claims data request"""
        self.log(f"[EXECUTE] Starting execution for task {task_id}")
        self.log(f"[EXECUTE] Request: {request}")

        task = self.context.get_task(task_id)
        if not task:
            self.log(f"[EXECUTE-ERROR] Task {task_id} not found")
            return "Task not found"

        try:
            self.log(f"[EXECUTE] Starting task {task_id}")
            task.start()
            self.context.update_task(task_id, TaskStatus.RUNNING)

            # Generate SQL
            self.log(f"[EXECUTE] Generating SQL query...")
            sql = self.generate_sql(request)
            self.context.store_query(f"med_query_{task_id}", sql)
            self.log(f"[EXECUTE] SQL stored with key: med_query_{task_id}")

            # Execute query
            self.log(f"[EXECUTE] Submitting query to BigQuery...")
            query_job = self.bq_client.query(sql)
            self.log(f"[EXECUTE] Query job created: {query_job.job_id}")

            results = query_job.result()
            self.log(f"[EXECUTE] Query completed")

            # Convert to Polars DataFrame
            rows = list(results)
            self.log(f"[EXECUTE] Retrieved {len(rows)} rows from BigQuery")

            if rows:
                df = pl.DataFrame([dict(row) for row in rows])
                self.log(f"[EXECUTE] Created DataFrame with shape: {df.shape}")
                self.log(f"[EXECUTE] DataFrame columns: {df.columns}")
            else:
                df = pl.DataFrame()
                self.log(f"[EXECUTE] Created empty DataFrame (no results)")

            # Store result
            self.context.store_dataframe(f"med_claims_{task_id}", df)
            self.log(f"[EXECUTE] DataFrame stored with key: med_claims_{task_id}")

            self.context.update_task(task_id, TaskStatus.COMPLETED, result=f"Found {len(df)} rows")
            self.log(f"[EXECUTE] Task {task_id} completed successfully with {len(df)} rows")

            return df

        except Exception as e:
            error_msg = f"Medical Claims query failed: {str(e)}"
            self.log(f"[EXECUTE-ERROR] {error_msg}")
            self.log(f"[EXECUTE-ERROR] Full exception: {repr(e)}")
            self.context.add_error(error_msg)
            self.context.update_task(task_id, TaskStatus.FAILED, error=error_msg)
            return error_msg

    def get_status(self, task_id: str) -> Dict[str, Any]:
        """Get status of a task"""
        task = self.context.get_task(task_id)
        if not task:
            return {"status": "not_found"}

        return {
            "status": task.status.value,
            "result": task.result,
            "error": task.error,
            "duration": (task.completed_at - task.started_at) if task.completed_at and task.started_at else None
        }