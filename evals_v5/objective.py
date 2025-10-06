"""Objective achievement evaluator"""
import json
from . import BaseEvaluator


class ObjectiveEvaluator(BaseEvaluator):
    """Check if agent achieved user's objective"""

    @property
    def name(self) -> str:
        return "objective"

    @property
    def prompt_template(self) -> str:
        return """Evaluate if objective was achieved:

User Objective: {objective}
Agent Actions: {actions}
Final Result: {result}

Check:
1. Was the stated objective fully met?
2. Were all requirements addressed?
3. Is the result complete and usable?
4. Were there unnecessary detours?

Respond ONLY with valid JSON:
{{
  "score": <0-100>,
  "passed": <true/false>,
  "unmet_requirements": ["req1"],
  "reasoning": "..."
}}
"""

    def _parse_result(self, result_text: str) -> dict:
        return json.loads(result_text)
