"""SQL query evaluator"""
import json
from . import BaseEvaluator


class SQLEvaluator(BaseEvaluator):
    """Validate SQL syntax and logic"""

    @property
    def name(self) -> str:
        return "sql"

    @property
    def prompt_template(self) -> str:
        return """Evaluate this SQL query for correctness:

Query: {sql}
Context: {context}

Check for:
1. Syntax errors
2. Logic errors (wrong JOINs, WHERE clauses)
3. Performance issues (missing indexes, full table scans)
4. Security issues (SQL injection risks)

Respond ONLY with valid JSON:
{{
  "score": <0-100>,
  "passed": <true/false>,
  "issues": ["issue1", "issue2"],
  "reasoning": "..."
}}
"""

    def _parse_result(self, result_text: str) -> dict:
        return json.loads(result_text)
