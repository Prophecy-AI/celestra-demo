"""
TextToSQLMed tool - Generate SQL for medical claims data
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


class TextToSQLMed(Tool):
    """Generate SQL for med_claims table queries"""

    def __init__(self):
        super().__init__(
            name="text_to_sql_med",
            description="Convert natural language request to SQL for med_claims table"
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
        table_name = "`unique-bonbon-472921-q8.Claims.medical_claims`"
        return prompts.get_system_prompt(current_date=current_date, table_name=table_name)

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        request = parameters["request"]
        tool_log("text_to_sql_med", f"Request: {request[:100]}...")

        try:
            tool_log("text_to_sql_med", "Calling Claude for SQL generation")
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0,
                system=self._build_system_prompt(),
                messages=[{"role": "user", "content": request}]
            )

            sql = response.content[0].text.strip()
            sql = re.sub(r'^```sql\s*', '', sql)
            sql = re.sub(r'\s*```$', '', sql)
            sql = sql.strip()

            if not sql.upper().startswith(('SELECT', 'WITH')):
                tool_log("text_to_sql_med", "Invalid SQL - doesn't start with SELECT/WITH", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error="Generated text does not appear to be valid SQL"
                )

            scope = self._extract_scope(sql, request)
            tool_log("text_to_sql_med", f"SQL generated ({len(sql)} chars), scope: {scope}", "success")
            tool_log("text_to_sql_med", f"SQL: {sql[:200]}...", "sql")

            try:
                sql_eval = evaluate_sql_correctness(sql, request, "med_claims")
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
            tool_log("text_to_sql_med", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"SQL generation failed: {str(e)}"
            )

    def _extract_intent(self, request: str) -> str:
        """Extract the main intent from the request"""
        request_lower = request.lower()

        if "provider" in request_lower or "hcp" in request_lower:
            if "count" in request_lower:
                return "provider counts"
            return "healthcare providers"
        elif "condition" in request_lower or "diagnosis" in request_lower:
            return "medical conditions"
        elif "procedure" in request_lower:
            return "medical procedures"
        elif "organization" in request_lower or "hco" in request_lower:
            return "healthcare organizations"
        else:
            return "medical claims data"

    def _extract_scope(self, sql: str, request: str) -> str:
        """Extract the scope of the query"""
        sql_upper = sql.upper()

        condition_match = re.search(r"condition_label[^']*LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        condition = condition_match.group(1) if condition_match else None

        state_match = re.search(r"STATE\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        state = state_match.group(1) if state_match else None

        date_match = re.search(r"STATEMENT[^><=]*([><=]+)\s*'(\d{4}-\d{2}-\d{2})'", sql, re.IGNORECASE)
        has_date_filter = date_match is not None

        scope_parts = []

        if condition:
            scope_parts.append(f"{condition}")

        if "PRIMARY_HCP" in sql_upper:
            scope_parts.append("providers")
        elif "PRIMARY_HCO" in sql_upper:
            scope_parts.append("organizations")

        if state:
            scope_parts.append(f"in {state}")

        if has_date_filter:
            scope_parts.append("with date filters")

        return " ".join(scope_parts) if scope_parts else "All relevant data"
