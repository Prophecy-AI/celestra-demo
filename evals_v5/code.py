"""Code correctness evaluator"""
import json
from . import BaseEvaluator


class CodeEvaluator(BaseEvaluator):
    """Verify generated code correctness"""

    @property
    def name(self) -> str:
        return "code"

    @property
    def prompt_template(self) -> str:
        return """Evaluate generated code:

Code: {code}
Purpose: {purpose}

Check:
1. Syntax correctness
2. Logic correctness
3. Edge case handling
4. Best practices

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
