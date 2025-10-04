"""
Template for generating SQL conversion tools
"""
from typing import Dict, Any, Optional
from .base_template import ToolTemplate


class SQLToolTemplate(ToolTemplate):
    """Template for generating text-to-SQL tools"""

    def get_config_schema(self) -> Dict[str, Any]:
        """Get the expected configuration schema"""
        return {
            "tool_name": "str (e.g., 'text_to_sql_pharmacy')",
            "class_name": "str (e.g., 'TextToSQLPharmacy')",
            "description": "str (brief description of what this tool does)",
            "table_name": "str (full BigQuery table name)",
            "key_columns": "list[dict] (list of column definitions)",
            "column_selection_priority": "str (guidance on column selection)",
            "aggregation_rules": "list[str] (list of aggregation guidelines)",
            "date_filtering": "Optional[str] (date filtering guidance)",
            "item_matching": "Optional[str] (matching/filtering guidance)",
            "output_format": "str (output format guidelines)",
            "lookup_context": "Optional[dict] (categorical values for reference)"
        }

    def validate_config(self, config: Dict[str, Any]) -> Optional[str]:
        """Validate configuration"""
        required_fields = ["tool_name", "class_name", "description", "table_name", "key_columns"]

        for field in required_fields:
            if field not in config:
                return f"Missing required field: {field}"

        if not isinstance(config["key_columns"], list):
            return "key_columns must be a list"

        if config["key_columns"]:
            for i, col in enumerate(config["key_columns"]):
                if not isinstance(col, dict):
                    return f"key_columns[{i}] must be a dictionary"
                if "name" not in col or "type" not in col or "description" not in col:
                    return f"key_columns[{i}] must have 'name', 'type', and 'description'"

        return None

    def generate_tool_code(self, config: Dict[str, Any]) -> str:
        """Generate Python code for SQL tool"""
        tool_name = config["tool_name"]
        class_name = config["class_name"]
        description = config["description"]

        code = f'''"""
SQL generation tool: {description}
"""
import os
import re
import anthropic
from typing import Dict, Any
from agent_v3.tools.base import Tool, ToolResult
from agent_v3.tools.logger import tool_log
from agent_v3.prompts.loader import PromptLoader
from evals.sql_evaluator import evaluate_sql_correctness


class {class_name}(Tool):
    """{description}"""

    def __init__(self):
        super().__init__(
            name="{tool_name}",
            description="{description}"
        )
        self.client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.prompt_loader = PromptLoader()

    def _build_system_prompt(self) -> str:
        """Load system prompt from YAML file"""
        from datetime import datetime

        variables = {{
            "table_name": "{config['table_name']}"
        }}

        # Add current_date if needed
        if "current_date" in self.prompt_loader.get_prompt_metadata("{tool_name}").get("variables", []):
            variables["current_date"] = datetime.now().strftime("%Y-%m-%d")

        return self.prompt_loader.load_prompt("{tool_name}", variables=variables)

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Generate SQL from natural language request"""
        error = self.validate_parameters(parameters, ["request"])
        if error:
            return ToolResult(success=False, data={{}}, error=error)

        request = parameters["request"]
        tool_log("{tool_name}", f"Request: {{request[:100]}}...")

        try:
            # Call LLM to generate SQL
            tool_log("{tool_name}", "Calling Claude for SQL generation")
            response = self.client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=2048,
                temperature=0,
                system=self._build_system_prompt(),
                messages=[{{"role": "user", "content": request}}]
            )

            # Extract SQL from response
            sql = response.content[0].text.strip()

            # Clean up SQL (remove markdown if present)
            sql = re.sub(r'^```sql\\s*', '', sql)
            sql = re.sub(r'\\s*```$', '', sql)
            sql = sql.strip()

            # Validate it looks like SQL
            if not sql.upper().startswith(('SELECT', 'WITH')):
                tool_log("{tool_name}", "Invalid SQL - doesn't start with SELECT/WITH", "error")
                return ToolResult(
                    success=False,
                    data={{}},
                    error="Generated text does not appear to be valid SQL"
                )

            # Extract estimated scope
            scope = self._extract_scope(sql, request)
            tool_log("{tool_name}", f"SQL generated ({{len(sql)}} chars), scope: {{scope}}", "success")

            # Evaluate SQL correctness
            try:
                sql_eval = evaluate_sql_correctness(sql, request, "{tool_name}")
                score = sql_eval.get('overall_score', 'N/A')
                reasoning = sql_eval.get('reasoning', 'No reasoning provided')
                print(f"✅ SQL Evaluation: {{score}} - {{reasoning}}")
            except Exception as e:
                sql_eval = {{"error": str(e)}}
                print(f"⚠️ SQL evaluation failed: {{e}}")

            return ToolResult(
                success=True,
                data={{
                    "sql": sql,
                    "explanation": f"Query for {{self._extract_intent(request)}}",
                    "estimated_scope": scope,
                    "evaluation": sql_eval
                }}
            )

        except Exception as e:
            tool_log("{tool_name}", f"Failed: {{str(e)}}", "error")
            return ToolResult(
                success=False,
                data={{}},
                error=f"SQL generation failed: {{str(e)}}"
            )

    def _extract_intent(self, request: str) -> str:
        """Extract the main intent from the request"""
        # Basic intent extraction - can be customized
        return request[:100] if len(request) > 100 else request

    def _extract_scope(self, sql: str, request: str) -> str:
        """Extract the scope of the query"""
        # Basic scope extraction - can be customized
        return "SQL query generated"
'''
        return code

    def generate_prompt(self, config: Dict[str, Any]) -> str:
        """Generate YAML prompt for SQL tool"""
        tool_name = config["tool_name"]
        description = config["description"]
        table_name = config["table_name"]
        key_columns = config["key_columns"]

        # Build columns section
        columns_section = []
        for col in key_columns:
            columns_section.append(f"  - {col['name']}: {col['type']} - {col['description']}")

        columns_str = "\n".join(columns_section)

        # Optional sections
        column_priority = config.get("column_selection_priority", "- Be selective with columns\n  - NEVER use SELECT *")
        aggregation_rules = config.get("aggregation_rules", ["- Use appropriate GROUP BY clauses"])
        aggregation_str = "\n".join(f"  {rule}" for rule in aggregation_rules)

        date_filtering = config.get("date_filtering", "")
        date_section = f"\n\n  DATE FILTERING:\n  {date_filtering}" if date_filtering else ""

        item_matching = config.get("item_matching", "")
        matching_section = f"\n\n  ITEM MATCHING:\n  {item_matching}" if item_matching else ""

        output_format = config.get("output_format", "- Return clean, executable BigQuery Standard SQL\n  - Include appropriate GROUP BY when using aggregations\n  - Add ORDER BY for meaningful result ordering\n  - LIMIT results to 1,000,000 (1M) rows")

        # Build lookup context if provided
        lookup_context = config.get("lookup_context", {})
        lookup_section = ""
        if lookup_context:
            lookup_lines = ["  ## LOOKUP CONTEXT", ""]
            lookup_lines.append("  - Curated categorical values:")
            for key, values in lookup_context.items():
                if isinstance(values, list):
                    values_str = ", ".join(str(v) for v in values)
                    lookup_lines.append(f"    - {key}: {values_str}")
            lookup_section = "\n" + "\n".join(lookup_lines)

        # Determine if we need current_date variable
        has_date_vars = "DATE" in date_filtering.upper() or "CURRENT_DATE" in table_name.upper()
        variables_section = ""
        if has_date_vars:
            variables_section = """variables:
  - current_date
  - table_name
"""
        else:
            variables_section = """variables:
  - table_name
"""

        # Check if current_date is needed in the prompt
        current_date_section = ""
        if has_date_vars:
            current_date_section = """
  CURRENT DATE: Today is {{ current_date }}. When users ask for "recent", "current", "this year", "last month", etc., use BigQuery date functions:
  - CURRENT_DATE() for today's date
  - DATE_SUB(CURRENT_DATE(), INTERVAL n DAY/MONTH/YEAR) for past periods
  - Example: "recent data" → WHERE date_field >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
"""

        prompt = f'''name: "{tool_name}"
description: "{description}"
model: "claude-sonnet-4-20250514"
temperature: 0
max_tokens: 2048
{variables_section}
system_prompt: |
  You are a BigQuery Standard SQL generator for {description}.

  TASK: Convert natural language queries into executable BigQuery Standard SQL.

  CRITICAL: Output ONLY the SQL query. No explanations, no descriptions, no text before or after the SQL.
{current_date_section}
  TABLE: {{{{ table_name }}}}

  KEY COLUMNS:
{columns_str}

  COLUMN SELECTION PRIORITY:
  {column_priority}

  AGGREGATION RULES:
{aggregation_str}
{date_section}
{matching_section}

  OUTPUT FORMAT:
  {output_format}
{lookup_section}
'''
        return prompt
