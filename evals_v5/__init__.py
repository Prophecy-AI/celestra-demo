"""Async evaluators using OpenAI o3"""
from abc import ABC, abstractmethod
from typing import Dict
from openai import AsyncOpenAI


class BaseEvaluator(ABC):
    """Base evaluator - all evals inherit from this"""

    @property
    @abstractmethod
    def name(self) -> str:
        pass

    @property
    @abstractmethod
    def prompt_template(self) -> str:
        pass

    async def evaluate(self, data: Dict, client: AsyncOpenAI) -> Dict:
        """Run eval using o3

        Args:
            data: Eval input data
            client: OpenAI client

        Returns:
            {"score": 0-100, "passed": bool, "reasoning": str, ...}
        """
        prompt = self.prompt_template.format(**data)

        response = await client.chat.completions.create(
            model="o3",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0
        )

        return self._parse_result(response.choices[0].message.content)

    @abstractmethod
    def _parse_result(self, result_text: str) -> Dict:
        """Parse o3 response into structured result"""
        pass
