"""Hallucination detection evaluator"""
import json
from . import BaseEvaluator


class HallucinationEvaluator(BaseEvaluator):
    """Check if agent's claims are supported by data"""

    @property
    def name(self) -> str:
        return "hallucination"

    @property
    def prompt_template(self) -> str:
        return """Check if the agent's answer is supported by the data:

Agent Answer: {answer}
Source Data: {data}

Verify:
1. All numerical claims are accurate
2. All facts are present in source data
3. No invented information
4. No misinterpretations

Respond ONLY with valid JSON:
{{
  "score": <0-100>,
  "passed": <true/false>,
  "hallucinations": ["claim1", "claim2"],
  "reasoning": "..."
}}
"""

    def _parse_result(self, result_text: str) -> dict:
        return json.loads(result_text)
