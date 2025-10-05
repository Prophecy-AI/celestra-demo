"""
TextToSQLProviderPayments tool - Generate SQL for provider payments data
"""
import os
import re
import anthropic
from typing import Dict, Any
from agent_v3.tools.base import Tool, ToolResult
from agent_v3.tools.logger import tool_log
from . import prompts


class TextToSQLProviderPayments(Tool):
    """Generate SQL for provider_payments table queries"""

    def __init__(self):
        super().__init__(
            name="text_to_sql_provider_payments",
            description="Convert natural language request to SQL for provider_payments table"
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
        table_name = "`unique-bonbon-472921-q8.HCP.provider_payments`"
        return prompts.get_system_prompt(table_name=table_name)

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        request = parameters["request"]
        tool_log("text_to_sql_provider_payments", f"Request: {request[:100]}...")

        try:
            tool_log("text_to_provider_payments", "Calling Claude for SQL generation")
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
                tool_log("text_to_sql_providers_payments", "Invalid SQL - doesn't start with SELECT/WITH", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error="Generated text does not appear to be valid SQL"
                )

            scope = self._extract_scope(sql, request)
            tool_log("text_to_sql_providers_payments", f"SQL generated ({len(sql)} chars), scope: {scope}", "success")
            tool_log("text_to_sql_providers_payments", f"SQL: {sql[:200]}...", "sql")

            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "explanation": f"Query to find {self._extract_intent(request)}",
                    "estimated_scope": scope
                }
            )

        except Exception as e:
            tool_log("text_to_sql_providers_payments", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"SQL generation failed: {str(e)}"
            )

    def _extract_intent(self, request: str) -> str:
        """Extract the main intent from the request"""
        request_lower = request.lower()

        if "payment" in request_lower or "amount" in request_lower or "total" in request_lower:
            return "provider payment amounts"
        elif "payer" in request_lower or "company" in request_lower:
            return "payer companies"
        elif "product" in request_lower or "drug" in request_lower or "associated product" in request_lower:
            return "associated products"
        elif "nature" in request_lower and "payment" in request_lower:
            return "nature of payment"
        elif "program year" in request_lower or "year" in request_lower:
            return "program year"
        elif "record id" in request_lower or "id" in request_lower:
            return "payment record id"
        elif "provider" in request_lower or "npi" in request_lower or "doctor" in request_lower:
            return "provider payment data"
        else:
            return "healthcare provider payment data"

    def _extract_scope(self, sql: str, request: str) -> str:
        """Extract the scope of the query"""
        return "payment data analysis"
