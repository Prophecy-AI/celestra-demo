"""
Answer Relevancy Evaluator for Agent V3
Evaluates if agent answers are relevant to user questions
"""
import os
import asyncio
from typing import Dict, Any, Optional
import json

# Load environment variables
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("🔍 Answer Evaluator: dotenv loaded")
except ImportError:
    print("🔍 Answer Evaluator: python-dotenv not available, using system env vars")

import openai


class AnswerEvaluator:
    """Evaluates relevancy of agent answers to user questions"""

    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the answer evaluation system prompt"""
        return """You are an expert evaluator assessing how well agent responses address user questions in healthcare data analysis contexts.

Your task is to evaluate whether the agent's answer directly and comprehensively addresses the user's original question.

EVALUATION CRITERIA:

1. QUESTION_ANSWERING (0.0-1.0):
   - Does the response directly answer what was asked?
   - Are the key points from the question addressed?
   - Is the response on-topic and focused?

2. COMPLETENESS (0.0-1.0):
   - Are all aspects of the question covered?
   - Are sufficient details provided?
   - Are follow-up questions or clarifications addressed?

3. CLARITY_COMPREHENSIVENESS (0.0-1.0):
   - Is the answer clear and easy to understand?
   - Are complex concepts explained appropriately?
   - Is the structure logical and well-organized?

4. ACTIONABILITY (0.0-1.0):
   - Does the answer provide actionable insights?
   - Are recommendations or next steps provided when appropriate?
   - Can the user act on the information provided?

HEALTHCARE CONTEXT CONSIDERATIONS:
- Prescription analyses should include relevant drug names, quantities, trends
- Provider analyses should include meaningful provider insights and patterns
- Claims data should be interpreted in healthcare business context
- Statistical results should be explained in practical terms
- Regulatory and compliance aspects should be considered when relevant

COMMON ANSWER QUALITY ISSUES:
- Generic responses that don't address specific questions
- Technical jargon without explanation
- Incomplete analysis of requested data
- Missing context for statistical findings
- Failure to provide actionable insights
- Answers that are too high-level or too detailed for the question

RESPONSE FORMAT (JSON):
{
  "question_answering": 0.91,
  "completeness": 0.87,
  "clarity_comprehensiveness": 0.93,
  "actionability": 0.85,
  "overall_relevancy": 0.89,
  "reasoning": "2-3 sentences comparing the user's question with the agent's answer, explaining key strengths and gaps",
  "explanation": "Brief explanation of answer quality assessment",
  "strengths": ["What the answer does well"],
  "improvement_areas": ["What could be improved"],
  "missing_elements": ["Key elements not addressed"]
}

Respond ONLY with the JSON object. No additional text."""

    async def evaluate_answer(self, user_question: str, agent_answer: str,
                            supporting_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate answer relevancy

        Args:
            user_question: Original user question
            agent_answer: The agent's response to evaluate
            supporting_data: Optional supporting data used in the answer

        Returns:
            Dictionary with answer evaluation scores
        """
        try:
            evaluation_prompt = f"""USER QUESTION: {user_question}

AGENT ANSWER:
{agent_answer}

SUPPORTING DATA CONTEXT: {supporting_data or "Not provided"}

Please evaluate how well the agent's answer addresses the user's original question."""

            response = await self.client.chat.completions.create(
                model="o3",
                messages=[
                    {"role": "user", "content": f"{self.system_prompt}\n\n{evaluation_prompt}"}
                ]
            )

            result_text = response.choices[0].message.content.strip()

            try:
                result = json.loads(result_text)
            except json.JSONDecodeError:
                result = {
                    "question_answering": 0.5,
                    "completeness": 0.5,
                    "clarity_comprehensiveness": 0.5,
                    "actionability": 0.5,
                    "overall_relevancy": 0.5,
                    "explanation": "Failed to parse evaluation response",
                    "strengths": ["JSON parsing error"],
                    "improvement_areas": ["Manual review required"],
                    "missing_elements": ["Manual review required"]
                }

            # Ensure all required fields exist
            required_fields = ["question_answering", "completeness", "clarity_comprehensiveness",
                             "actionability", "overall_relevancy", "reasoning", "explanation",
                             "strengths", "improvement_areas", "missing_elements"]
            for field in required_fields:
                if field not in result:
                    if field in ["question_answering", "completeness", "clarity_comprehensiveness",
                               "actionability", "overall_relevancy"]:
                        result[field] = 0.5
                    else:
                        result[field] = ["Not evaluated"] if field in ["strengths", "improvement_areas", "missing_elements"] else "Not evaluated"

            return result

        except Exception as e:
            return {
                "question_answering": 0.0,
                "completeness": 0.0,
                "clarity_comprehensiveness": 0.0,
                "actionability": 0.0,
                "overall_relevancy": 0.0,
                "explanation": f"Evaluation failed: {str(e)}",
                "strengths": [],
                "improvement_areas": ["Evaluation system error"],
                "missing_elements": ["Manual review required"]
            }

    def evaluate_answer_sync(self, user_question: str, agent_answer: str,
                           supporting_data: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for answer evaluation

        Args:
            user_question: Original user question
            agent_answer: The agent's response to evaluate
            supporting_data: Optional supporting data used in the answer

        Returns:
            Dictionary with answer evaluation scores
        """
        try:
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(self.evaluate_answer(user_question, agent_answer, supporting_data))
        except RuntimeError:
            # Create new event loop if none exists
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(self.evaluate_answer(user_question, agent_answer, supporting_data))
            finally:
                loop.close()


# Global instance for easy import
answer_evaluator = AnswerEvaluator()


def evaluate_answer_relevancy(user_question: str, agent_answer: str,
                            supporting_data: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to evaluate answer relevancy

    Args:
        user_question: Original user question
        agent_answer: The agent's response to evaluate
        supporting_data: Optional supporting data used in the answer

    Returns:
        Dictionary with answer evaluation scores
    """
    return answer_evaluator.evaluate_answer_sync(user_question, agent_answer, supporting_data)