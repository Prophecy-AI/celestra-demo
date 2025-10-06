"""Retrieval relevance evaluator"""
import json
from . import BaseEvaluator


class RetrievalEvaluator(BaseEvaluator):
    """Check if SQL query returns relevant data"""

    @property
    def name(self) -> str:
        return "retrieval"

    @property
    def prompt_template(self) -> str:
        return """Evaluate if this SQL query retrieves relevant data:

Query: {sql}
User Question: {question}
Retrieved Data Sample: {data_sample}

Check:
1. Does query answer the user's question?
2. Are the selected columns relevant?
3. Are filters appropriate?
4. Is the data actually useful?

Respond ONLY with valid JSON:
{{
  "score": <0-100>,
  "passed": <true/false>,
  "issues": ["issue1"],
  "reasoning": "..."
}}
"""

    def _parse_result(self, result_text: str) -> dict:
        return json.loads(result_text)
