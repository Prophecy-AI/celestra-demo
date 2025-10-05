"""
TextToSQLProvidersBio tool - Generate SQL for provider biographical data
"""
import os
import re
import anthropic
from typing import Dict, Any, Optional, TYPE_CHECKING
from agent_v3.tools.base import Tool, ToolResult
from agent_v3.tools.categories import ToolCategory
from agent_v3.tools.logger import tool_log
from . import prompts

if TYPE_CHECKING:
    from agent_v3.context import Context


class TextToSQLProvidersBio(Tool):
    """Generate SQL for providers_bio table queries"""

    def __init__(self):
        super().__init__(
            name="text_to_sql_providers_bio",
            description="Convert natural language request to SQL for providers_bio table",
            category=ToolCategory.SQL_GENERATION
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
        table_name = "`unique-bonbon-472921-q8.HCP.providers_bio`"
        return prompts.get_system_prompt(table_name=table_name)

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        request = parameters["request"]
        tool_log("text_to_sql_providers_bio", f"Request: {request[:100]}...")

        try:
            tool_log("text_to_sql_providers_bio", "Calling Claude for SQL generation")
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
                tool_log("text_to_sql_providers_bio", "Invalid SQL - doesn't start with SELECT/WITH", "error")
                return ToolResult(
                    success=False,
                    data={},
                    error="Generated text does not appear to be valid SQL"
                )

            scope = self._extract_scope(sql, request)
            tool_log("text_to_sql_providers_bio", f"SQL generated ({len(sql)} chars), scope: {scope}", "success")
            tool_log("text_to_sql_providers_bio", f"SQL: {sql[:200]}...", "sql")

            return ToolResult(
                success=True,
                data={
                    "sql": sql,
                    "explanation": f"Query to find {self._extract_intent(request)}",
                    "estimated_scope": scope
                }
            )

        except Exception as e:
            tool_log("text_to_sql_providers_bio", f"Failed: {str(e)}", "error")
            return ToolResult(
                success=False,
                data={},
                error=f"SQL generation failed: {str(e)}"
            )

    def _extract_intent(self, request: str) -> str:
        """Extract the main intent from the request"""
        request_lower = request.lower()

        if "specialty" in request_lower:
            return "provider specialties"
        elif "certification" in request_lower:
            return "provider certifications"
        elif "education" in request_lower or "school" in request_lower or "university" in request_lower:
            return "provider education"
        elif "award" in request_lower:
            return "provider awards"
        elif "membership" in request_lower:
            return "provider memberships"
        elif "condition" in request_lower and "treat" in request_lower:
            return "conditions treated by providers"
        elif "provider" in request_lower or "npi" in request_lower:
            return "provider biographical data"
        else:
            return "healthcare provider data"

    def _extract_scope(self, sql: str, request: str) -> str:
        """Extract the scope of the query"""
        scope_parts = []

        specialty_match = re.search(r"SPECIALTY\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        if specialty_match:
            scope_parts.append(f"specialty: {specialty_match.group(1)}")

        cert_match = re.search(r"CERTIFICATIONS\s+LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        if cert_match:
            scope_parts.append(f"certification: {cert_match.group(1)}")

        education_match = re.search(r"EDUCATION\s+LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        if education_match:
            scope_parts.append(f"education: {education_match.group(1)}")

        awards_match = re.search(r"AWARDS\s+LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        if awards_match:
            scope_parts.append(f"award: {awards_match.group(1)}")

        membership_match = re.search(r"MEMBERSHIPS\s+LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        if membership_match:
            scope_parts.append(f"membership: {membership_match.group(1)}")

        conditions_match = re.search(r"CONDITIONS_TREATED\s+LIKE\s+'%([^%]+)%'", sql, re.IGNORECASE)
        if conditions_match:
            scope_parts.append(f"condition treated: {conditions_match.group(1)}")

        state_match = re.search(r"STATE\s*=\s*'([^']+)'", sql, re.IGNORECASE)
        if state_match:
            scope_parts.append(f"state: {state_match.group(1)}")

        if not scope_parts:
            scope_parts.append("provider biographical data")

        return " ".join(scope_parts) if scope_parts else "All relevant data"

    def get_success_hint(self, context: 'Context') -> Optional[str]:
        """Provide hint after successful SQL generation"""
        from agent_v3.prompts import hints
        return hints.get_sql_generated_hint()
