"""
RX Claims Agent - handles pharmacy claims queries
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
from .colors import *

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.rx_claims_prompt import SYSTEM_PROMPT as RX_CLAIMS_PROMPT

load_dotenv()

class RXClaimsAgent:
    def __init__(self, context: SharedContext, session_id: str):
        self.context = context
        self.session_id = session_id
        self.bq_client = bigquery.Client(project=os.getenv("GCP_PROJECT"))
        self.anthropic_client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        # Dataset is hardcoded in the rx_claims_prompt.py already
        self.debug = os.getenv('DEBUG', '0') == '1'

    def log(self, message: str):
        """Colored debug logging"""
        if self.debug:
            timestamp = f"{TIMESTAMP}[{time.strftime('%H:%M:%S')}]{RESET}"
            component = f"{COMPONENT}[RX-AGENT]{RESET}"

            # Color based on content
            if "ERROR" in message or "failed" in message.lower():
                color = ERROR
            elif "SQL" in message or "Query" in message:
                color = SQL
            elif "completed" in message or "success" in message.lower():
                color = SUCCESS
            elif "DataFrame" in message or "rows" in message:
                color = DATA
            else:
                color = RESET

            print(f"{timestamp} {component} {color}{message}{RESET}")

    def generate_sql(self, request: str) -> str:
        """Generate SQL query from natural language request"""
        self.log(f"[SQL-GEN] Generating SQL for request: {request}")
        self.log(f"[SQL-GEN] Using system prompt of length: {len(RX_CLAIMS_PROMPT)}")

        response = self.anthropic_client.messages.create(
            model="claude-sonnet-4-20250514",
            max_tokens=4096,
            temperature=0,
            system=RX_CLAIMS_PROMPT,
            messages=[{"role": "user", "content": request}],
        )

        # Extract text content from response (skip thinking blocks)
        sql = ""
        for block in response.content:
            if hasattr(block, 'type'):
                if block.type == 'thinking':
                    self.log(f"[SQL-THINKING] Model thinking: {block.thinking[:200]}...")
                elif block.type == 'text':
                    sql += block.text
            else:
                # Fallback for simple text response
                sql = block.text if hasattr(block, 'text') else str(block)

        sql = sql.strip().replace("```sql", "").replace("```", "").strip()

        self.log(f"[SQL-GEN] Generated SQL: {sql}")
        return sql

    def execute(self, task_id: str, request: str) -> Union[pl.DataFrame, str]:
        """Execute RX claims data request"""
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
            self.context.store_query(f"rx_query_{task_id}", sql)
            self.log(f"[EXECUTE] SQL stored with key: rx_query_{task_id}")

            # Execute query
            self.log(f"[EXECUTE] Submitting query to BigQuery...")
            query_job = self.bq_client.query(sql)
            self.log(f"[EXECUTE] Query job created: {query_job.job_id}")

            results = query_job.result()
            self.log(f"[EXECUTE] Query completed")

            # Convert to Polars DataFrame
            rows = results.to_arrow()
            df = pl.from_arrow(rows)
            self.log(f"[EXECUTE] Retrieved {len(rows)} rows from BigQuery")

            if not df.is_empty():
                self.log(f"[EXECUTE] Created DataFrame with shape: {df.shape}")
                self.log(f"[EXECUTE] DataFrame columns: {df.columns}")
            else:
                self.log(f"[EXECUTE] Created empty DataFrame (no results)")

            # Store result
            self.context.store_dataframe(f"rx_claims_{task_id}", df)
            self.log(f"[EXECUTE] DataFrame stored with key: rx_claims_{task_id}")

            # Save to CSV with LLM-generated descriptive name
            if not df.is_empty():
                try:
                    output_dir = f"output/session_{self.session_id}"
                    os.makedirs(output_dir, exist_ok=True)

                    # Generate descriptive filename using task request
                    prompt = f"""Generate a short descriptive CSV filename (3-5 words, use underscores).
Task request: {request[:200]}
Data columns: {df.columns[:5]}
Row count: {len(df)}
Reply with ONLY the filename without .csv extension"""

                    try:
                        response = self.anthropic_client.messages.create(
                            model="claude-4-sonnet-20250514",
                            max_tokens=50,
                            messages=[{"role": "user", "content": prompt}],
                            temperature=0
                        )

                        suggested_name = response.content[0].text.strip().lower().replace(" ", "_").replace("-", "_")
                        suggested_name = suggested_name.replace(".csv", "")
                        suggested_name = "".join(c for c in suggested_name if c.isalnum() or c == "_")

                        file_name = f"rx_{task_id}_{suggested_name}.csv"
                        self.log(f"[EXECUTE] Generated filename: {file_name}")
                    except Exception as e:
                        self.log(f"[EXECUTE] Error generating filename: {e}")
                        file_name = f"rx_{task_id}.csv"

                    file_path = f"{output_dir}/{file_name}"
                    df.write_csv(file_path)
                    self.log(f"[EXECUTE] Saved CSV to: {file_path}")

                except Exception as e:
                    self.log(f"[EXECUTE] Error saving CSV: {e}")

            self.context.update_task(task_id, TaskStatus.COMPLETED, result=f"Found {len(df)} rows")
            self.log(f"[EXECUTE] Task {task_id} completed successfully with {len(df)} rows")

            return df

        except Exception as e:
            error_msg = f"RX Claims query failed: {str(e)}"
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