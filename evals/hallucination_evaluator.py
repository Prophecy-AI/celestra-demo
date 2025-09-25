"""
Hallucination Detector for Agent V3
Detects hallucinations in final responses with medical domain knowledge
"""
import os
import asyncio
import openai
from typing import Dict, Any, Optional
import json


class HallucinationEvaluator:
    """Detects hallucinations in agent responses for medical domain"""

    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the hallucination detection system prompt"""
        return """You are a medical domain expert evaluating healthcare data analysis responses for hallucinations and accuracy.

Your task is to detect potential hallucinations, inaccuracies, or unsupported claims in responses about healthcare claims data analysis.

EVALUATION CRITERIA:

1. FACTUAL_ACCURACY (0.0-1.0):
   - Are medical terms used correctly?
   - Are healthcare concepts accurately described?
   - Are statistical interpretations sound?

2. DATA_CONSISTENCY (0.0-1.0):
   - Do the claims align with the provided data?
   - Are numbers and statistics correctly interpreted?
   - Are conclusions supported by evidence?

3. MEDICAL_KNOWLEDGE (0.0-1.0):
   - Are drug names, conditions, procedures correctly referenced?
   - Are medical relationships and causations accurate?
   - Are healthcare industry terms used appropriately?

4. LOGICAL_COHERENCE (0.0-1.0):
   - Does the response follow logical reasoning?
   - Are conclusions well-supported by the data?
   - Are there contradictions or inconsistencies?

COMMON HALLUCINATION PATTERNS TO DETECT:
- Made-up drug names or NDC codes
- Incorrect medical terminology or definitions
- Unsupported statistical claims
- Fabricated healthcare provider information
- Incorrect procedure codes or descriptions
- Misinterpreted data relationships
- Claims not supported by the provided data

MEDICAL CONTEXT:
- NDC codes identify specific medications
- NPI numbers identify healthcare providers
- ICD/CPT codes identify diagnoses/procedures
- Claims data represents actual healthcare transactions
- Statistical patterns should reflect real healthcare trends

RESPONSE FORMAT (JSON):
{
  "factual_accuracy": 0.92,
  "data_consistency": 0.87,
  "medical_knowledge": 0.95,
  "logical_coherence": 0.89,
  "hallucination_risk": 0.15,
  "overall_confidence": 0.91,
  "reasoning": "2-3 sentences explaining the evaluation with specific examples from the response and medical domain knowledge",
  "explanation": "Brief explanation of evaluation",
  "potential_issues": ["List of potential hallucinations or inaccuracies"],
  "recommendations": ["Suggestions for improvement"]
}

Respond ONLY with the JSON object. No additional text."""

    async def evaluate_response(self, response: str, query_data: Optional[str] = None,
                              user_question: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate response for hallucinations

        Args:
            response: The agent's response to evaluate
            query_data: Optional data that was used to generate the response
            user_question: Original user question for context

        Returns:
            Dictionary with hallucination evaluation scores
        """
        try:
            evaluation_prompt = f"""AGENT RESPONSE TO EVALUATE:
{response}

USER QUESTION: {user_question or "Not provided"}

QUERY DATA CONTEXT: {query_data or "Not provided"}

Please evaluate this healthcare data analysis response for potential hallucinations, inaccuracies, or unsupported claims."""

            response_obj = await self.client.chat.completions.create(
                model="o1-preview",
                messages=[
                    {"role": "user", "content": f"{self.system_prompt}\n\n{evaluation_prompt}"}
                ],
                temperature=1,
                max_tokens=2000
            )

            result_text = response_obj.choices[0].message.content.strip()

            # Parse JSON response
            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                result = {
                    "factual_accuracy": 0.5,
                    "data_consistency": 0.5,
                    "medical_knowledge": 0.5,
                    "logical_coherence": 0.5,
                    "hallucination_risk": 0.5,
                    "overall_confidence": 0.5,
                    "explanation": "Failed to parse evaluation response",
                    "potential_issues": ["JSON parsing error"],
                    "recommendations": ["Manual review required"]
                }

            # Ensure all required fields exist
            required_fields = ["factual_accuracy", "data_consistency", "medical_knowledge",
                             "logical_coherence", "hallucination_risk", "overall_confidence",
                             "reasoning", "explanation", "potential_issues", "recommendations"]
            for field in required_fields:
                if field not in result:
                    if field in ["factual_accuracy", "data_consistency", "medical_knowledge",
                               "logical_coherence", "hallucination_risk", "overall_confidence"]:
                        result[field] = 0.5
                    else:
                        result[field] = "Not evaluated"

            return result

        except Exception as e:
            return {
                "factual_accuracy": 0.0,
                "data_consistency": 0.0,
                "medical_knowledge": 0.0,
                "logical_coherence": 0.0,
                "hallucination_risk": 1.0,
                "overall_confidence": 0.0,
                "explanation": f"Evaluation failed: {str(e)}",
                "potential_issues": ["Evaluation system error"],
                "recommendations": ["Manual review required"]
            }

    def evaluate_response_sync(self, response: str, query_data: Optional[str] = None,
                             user_question: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for response evaluation

        Args:
            response: The agent's response to evaluate
            query_data: Optional data that was used to generate the response
            user_question: Original user question for context

        Returns:
            Dictionary with hallucination evaluation scores
        """
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.evaluate_response(response, query_data, user_question))
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.evaluate_response(response, query_data, user_question))
            finally:
                loop.close()


# Global instance for easy import
hallucination_evaluator = HallucinationEvaluator()


def evaluate_hallucination(response: str, query_data: Optional[str] = None,
                         user_question: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to evaluate response for hallucinations

    Args:
        response: The agent's response to evaluate
        query_data: Optional data that was used to generate the response
        user_question: Original user question for context

    Returns:
        Dictionary with hallucination evaluation scores
    """
    return hallucination_evaluator.evaluate_response_sync(response, query_data, user_question)