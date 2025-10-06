"""Answer quality evaluator"""
import json
from . import BaseEvaluator


class AnswerEvaluator(BaseEvaluator):
    """Check answer quality against question"""

    @property
    def name(self) -> str:
        return "answer"

    @property
    def prompt_template(self) -> str:
        return """Evaluate answer quality:

Question: {question}
Answer: {answer}

Check:
1. Does answer address the question?
2. Is answer complete?
3. Is answer clear and well-structured?
4. Are insights actionable?

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
