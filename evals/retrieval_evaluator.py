"""
Retrieval Relevancy Evaluator for Agent V3
Evaluates if retrieved data is relevant to user queries
"""
import os
import asyncio
from typing import Dict, Any, Optional
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("🔍 Retrieval Evaluator: dotenv loaded")
except ImportError:
    print("🔍 Retrieval Evaluator: python-dotenv not available, using system env vars")

import openai


class RetrievalEvaluator:
    """Evaluates relevancy of retrieved data to user queries"""

    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the retrieval evaluation system prompt"""
        return """You are an expert evaluator assessing the relevancy of retrieved healthcare claims data to user queries.

Your task is to evaluate how well the retrieved data matches the user's information needs and query intent.

EVALUATION CRITERIA:

1. QUERY_ALIGNMENT (0.0-1.0):
   - Does the retrieved data directly address the user's question?
   - Are the relevant entities (drugs, providers, conditions) included?
   - Does the data scope match the query scope?

2. COMPLETENESS (0.0-1.0):
   - Does the data contain sufficient information to answer the query?
   - Are all requested dimensions/metrics present?
   - Is the date range and geographic scope appropriate?

3. DATA_QUALITY (0.0-1.0):
   - Is the data clean and well-structured?
   - Are there appropriate number of records (not too few, not too many)?
   - Do the values appear reasonable for the query context?

4. CONTEXT_RELEVANCE (0.0-1.0):
   - Is the retrieved data contextually appropriate?
   - Do the data patterns make sense for the query domain?
   - Are related/supporting data elements included?

HEALTHCARE CONTEXT CONSIDERATIONS:
- Prescription data should include drug names, prescribers, quantities, dates
- Medical claims should include providers, diagnoses, procedures, costs
- Provider queries need NPI numbers, names, locations
- Drug queries need NDC codes, drug names, therapeutic classes
- Time-based queries need appropriate date ranges
- Geographic queries need state/zip code filters

RESPONSE FORMAT (JSON):
{
  "query_alignment": 0.89,
  "completeness": 0.82,
  "data_quality": 0.91,
  "context_relevance": 0.87,
  "overall_relevancy": 0.87,
  "reasoning": "2-3 sentences explaining how well the retrieved data matches the user query with specific examples",
  "explanation": "Brief explanation of relevancy assessment",
  "strengths": ["What aspects of the retrieval worked well"],
  "weaknesses": ["What could be improved"],
  "recommendations": ["Suggestions for better retrieval"]
}

Respond ONLY with the JSON object. No additional text."""

    async def evaluate_retrieval(self, user_query: str, retrieved_data: Any,
                               sql_query: Optional[str] = None) -> Dict[str, Any]:
        """
        Evaluate retrieval relevancy

        Args:
            user_query: Original user question/request
            retrieved_data: The data retrieved from the database
            sql_query: The SQL query used to retrieve the data (optional)

        Returns:
            Dictionary with retrieval evaluation scores
        """
        if not os.getenv("ENABLE_EVALS", "false").lower() == "true":
            return {"evaluation_disabled": True}

        try:
            # Convert retrieved data to string representation
            if isinstance(retrieved_data, (list, dict)):
                data_str = json.dumps(retrieved_data, default=str, indent=2)[:2000]  # Limit size
            else:
                data_str = str(retrieved_data)[:2000]

            evaluation_prompt = f"""USER QUERY: {user_query}

SQL USED: {sql_query or "Not provided"}

RETRIEVED DATA:
{data_str}

Please evaluate how well the retrieved data addresses the user's query and information needs."""

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
                    "query_alignment": 0.5,
                    "completeness": 0.5,
                    "data_quality": 0.5,
                    "context_relevance": 0.5,
                    "overall_relevancy": 0.5,
                    "explanation": "Failed to parse evaluation response",
                    "strengths": ["JSON parsing error"],
                    "weaknesses": ["Manual review required"],
                    "recommendations": ["Manual review required"]
                }

            # Ensure all required fields exist
            required_fields = ["query_alignment", "completeness", "data_quality",
                             "context_relevance", "overall_relevancy", "reasoning", "explanation",
                             "strengths", "weaknesses", "recommendations"]
            for field in required_fields:
                if field not in result:
                    if field in ["query_alignment", "completeness", "data_quality",
                               "context_relevance", "overall_relevancy"]:
                        result[field] = 0.5
                    else:
                        result[field] = ["Not evaluated"] if field in ["strengths", "weaknesses", "recommendations"] else "Not evaluated"

            return result

        except Exception as e:
            return {
                "query_alignment": 0.0,
                "completeness": 0.0,
                "data_quality": 0.0,
                "context_relevance": 0.0,
                "overall_relevancy": 0.0,
                "explanation": f"Evaluation failed: {str(e)}",
                "strengths": [],
                "weaknesses": ["Evaluation system error"],
                "recommendations": ["Manual review required"]
            }

    def evaluate_retrieval_sync(self, user_query: str, retrieved_data: Any,
                              sql_query: Optional[str] = None) -> Dict[str, Any]:
        """
        Synchronous wrapper for retrieval evaluation

        Args:
            user_query: Original user question/request
            retrieved_data: The data retrieved from the database
            sql_query: The SQL query used to retrieve the data (optional)

        Returns:
            Dictionary with retrieval evaluation scores
        """
        print(f"🔍 Retrieval Evaluator: Starting evaluation")
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.evaluate_retrieval(user_query, retrieved_data, sql_query))
            print(f"🔍 Retrieval Evaluator: Evaluation completed, score: {result.get('overall_relevancy', 'N/A')}")
            return result
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.evaluate_retrieval(user_query, retrieved_data, sql_query))
                print(f"🔍 Retrieval Evaluator: Evaluation completed, score: {result.get('overall_relevancy', 'N/A')}")
                return result
            finally:
                loop.close()


# Global instance for easy import
retrieval_evaluator = RetrievalEvaluator()


def evaluate_retrieval_relevancy(user_query: str, retrieved_data: Any,
                                sql_query: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to evaluate retrieval relevancy

    Args:
        user_query: Original user question/request
        retrieved_data: The data retrieved from the database
        sql_query: The SQL query used to retrieve the data (optional)

    Returns:
        Dictionary with retrieval evaluation scores
    """
    if not os.getenv("ENABLE_EVALS", "false").lower() == "true":
        return {"evaluation_disabled": True}
    return retrieval_evaluator.evaluate_retrieval_sync(user_query, retrieved_data, sql_query)