"""
TextToSQLRx tool - Generate SQL for Rx claims data
"""
import os
import re
import anthropic
from datetime import datetime
from typing import Dict, Any
from agent_v3.tools.base import Tool, ToolResult
from agent_v3.tools.logger import tool_log
from evals.sql_evaluator import evaluate_sql_correctness
from . import prompts


class TextToSQLRx(Tool):
    """Generate SQL for rx_claims table queries"""

    def __init__(self):
        super().__init__(
            name="text_to_sql_rx",
            description="Convert natural language request to SQL for rx_claims table"
        )
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

    @classmethod
    def get_orchestrator_info(cls) -> str:
        """Return tool description for orchestrator system prompt"""
        return prompts.get_orchestrator_info()

    @classmethod
    def get_system_prompt(cls, **variables) -> str:
        """Return system prompt for LLM"""
        return prompts.get_system_prompt(**variables)

    def _build_system_prompt(self) -> str:
        """Build system prompt with current variables"""
        current_date = datetime.now().strftime("%Y-%m-%d")
        table_name = "`unique-bonbon-472921-q8.Claims.rx_claims`"
        return prompts.get_system_prompt(current_date=current_date, table_name=table_name)

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        request = parameters["request"]
        tool_log("text_to_sql_rx", f"Request: {request}...")

        try:
            # Call LLM to generate SQL
            tool_log("text_to_sql_rx", "Calling Claude for SQL generation")
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0,
                system=self._build_system_prompt(),
                messages=[{"role": "user", "content": request}]
            )

            # Extract SQL from response
            sql = response.content[0].text.strip()

            # Clean up SQL (remove markdown if present)
            sql = re.sub(r'^```sql\s*', '', sql)
            sql = re.sub(r'\s*```$', '', sql)
            sql = sql.strip()

            # Validate it looks like SQL
            if not sql.upper().startswith(('SELECT', 'WITH')):
                tool_log("text_to_sql_rx", "Invalid SQL - doesn't start with SELECT/WITH", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error="Generated text does not appear to be valid SQL"
                )

            # Extract estimated scope from the SQL
            scope = self._extract_scope(sql, request)
            tool_log("text_to_sql_rx", f"SQL generated ({len(sql)} chars), scope: {scope}", "success")
            tool_log("text_to_sql_rx", f"SQL: {sql}...", "sql")

            # Evaluate SQL correctness
            try:
                sql_eval = evaluate_sql_correctness(sql, request, "rx_claims")
                score = sql_eval.get('overall_score', 'N/A')
                reasoning = sql_eval.get('reasoning', 'No reasoning provided')
                print(f"✅ SQL Evaluation: {score} - {reasoning}")
            except Exception as e:
                sql_eval = {"error": str(e)}
                print(f"⚠️ SQL evaluation failed: {e}")

            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "explanation": f"Query to find {self._extract_intent(request)}",
                    "estimated_scope": scope,
                    "evaluation": sql_eval
                }
            )

        except Exception as e:
            tool_log("text_to_sql_rx", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"SQL generation failed: {str(e)}"
            )

    def _extract_intent(self, request: str) -> str:
        """Extract the main intent from the request"""
        request_lower = request.lower()

        if "prescriber" in request_lower:
            if "count" in request_lower:
                return "prescriber counts"
            return "prescribers"
        elif "drug" in request_lower or "medication" in request_lower:
            return "drug/medication data"
        elif "prescription" in request_lower:
            return "prescription data"
        else:
            return "healthcare data"

    def _extract_scope(self, sql: str, request: str) -> str:
        """Extract the scope of the query"""
        sql_upper = sql.upper()

        # Look for drug names
        drug_match = re.search(r"LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        drug_name = drug_match.group(1) if drug_match else None

        # Look for state filters
        state_match = re.search(r"STATE_CD\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        state = state_match.group(1) if state_match else None

        # Look for date ranges
        date_match = re.search(r"DATE[^><=]*([><=]+)\s*'(\d{4}-\d{2}-\d{2})'", sql, re.IGNORECASE)
        has_date_filter = date_match is not None

        # Build scope description
        scope_parts = []

        if drug_name:
            scope_parts.append(f"{drug_name}")

        if "PRESCRIBER" in sql_upper:
            scope_parts.append("prescribers")
        elif "PRESCRIPTION" in sql_upper or "RX" in sql_upper:
            scope_parts.append("prescriptions")

        if state:
            scope_parts.append(f"in {state}")

        if has_date_filter:
            scope_parts.append("with date filters")

        return " ".join(scope_parts) if scope_parts else "All relevant data"
