"""
SQL Correctness Evaluator for Agent V3
Evaluates SQL generation quality using GPT-4
"""
import os
import asyncio
from typing import Dict, Any, Optional
import json

try:
    from dotenv import load_dotenv
    load_dotenv()
    print("🔍 SQL Evaluator: dotenv loaded")
except ImportError:
    print("🔍 SQL Evaluator: python-dotenv not available, using system env vars")

import openai


class SQLEvaluator:
    """Evaluates SQL query correctness and quality"""

    def __init__(self):
        self.client = openai.AsyncOpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )
        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build the evaluation system prompt"""
        return """You are an expert SQL evaluator specializing in BigQuery Standard SQL for healthcare data.

Your task is to evaluate SQL queries generated for healthcare claims analysis and provide scores from 0.0 to 1.0 for different aspects.

EVALUATION CRITERIA:

1. SYNTAX_CORRECTNESS (0.0-1.0):
   - Is the SQL syntactically valid BigQuery Standard SQL?
   - Are parentheses, quotes, and semicolons properly placed?
   - Are keywords spelled correctly?

2. QUERY_LOGIC (0.0-1.0):
   - Does the query logic make sense for the user request?
   - Are JOINs, WHERE clauses, and aggregations appropriate?
   - Is the query likely to return meaningful results?

3. SCHEMA_COMPLIANCE (0.0-1.0):
   - Are referenced table names valid for the schema?
   - Are column names correctly referenced?
   - Are data types handled appropriately?

4. PERFORMANCE_EFFICIENCY (0.0-1.0):
   - Is the query reasonably efficient?
   - Are appropriate indexes/partitions considered?
   - Is unnecessary data selection avoided?

EXPECTED SCHEMAS:
- rx_claims table: PRESCRIBER_NPI_NBR, NDC, NDC_DRUG_NM, SERVICE_DATE_DD, TOTAL_PAID_AMT, etc.
- med_claims table: PRIMARY_HCP, condition_label, PROCEDURE_CD, STATEMENT_FROM_DD, CLAIM_CHARGE_AMT, etc.

RESPONSE FORMAT (JSON):
{
  "syntax_correctness": 0.95,
  "query_logic": 0.87,
  "schema_compliance": 0.92,
  "performance_efficiency": 0.83,
  "overall_score": 0.89,
  "reasoning": "2-3 sentences explaining the overall evaluation with specific examples from the query",
  "explanation": "Brief explanation of scores",
  "issues": ["List of specific issues found"],
  "suggestions": ["List of improvement suggestions"]
}

Respond ONLY with the JSON object. No additional text."""

    async def evaluate_sql(self, sql: str, user_request: str, table_type: str) -> Dict[str, Any]:
        """
        Evaluate SQL query quality

        Args:
            sql: The generated SQL query
            user_request: Original user request
            table_type: 'rx_claims' or 'med_claims'

        Returns:
            Dictionary with evaluation scores and feedback
        """
        if not os.getenv("ENABLE_EVALS", "false").lower() == "true":
            return {"evaluation_disabled": True}

        try:
            print(f"🔍 SQL Evaluator: Calling OpenAI o3 for evaluation")
            evaluation_prompt = f"""USER REQUEST: {user_request}

TABLE TYPE: {table_type}

GENERATED SQL:
```sql
{sql}
```

Please evaluate this SQL query according to the criteria and provide scores."""

            response = await self.client.chat.completions.create(
                model="o3",
                messages=[
                    {"role": "user", "content": f"{self.system_prompt}\n\n{evaluation_prompt}"}
                ]
            )
            print(f"🔍 SQL Evaluator: OpenAI API call completed")

            result_text = response.choices[0].message.content.strip()
            print(f"🔍 SQL Evaluator: Raw response length: {len(result_text)} chars")
            print(f"🔍 SQL Evaluator: Response preview: {result_text[:200]}...")

            try:
                result = json.loads(result_text)
                print(f"🔍 SQL Evaluator: Successfully parsed JSON, overall_score: {result.get('overall_score', 'missing')}")
            except json.JSONDecodeError as e:
                print(f"🔍 SQL Evaluator: JSON parsing failed: {e}")
                result = {
                    "syntax_correctness": 0.5,
                    "query_logic": 0.5,
                    "schema_compliance": 0.5,
                    "performance_efficiency": 0.5,
                    "overall_score": 0.5,
                    "explanation": "Failed to parse evaluation response",
                    "issues": ["JSON parsing error"],
                    "suggestions": ["Manual review required"]
                }

            # Ensure all required fields exist
            required_fields = ["syntax_correctness", "query_logic", "schema_compliance",
                             "performance_efficiency", "overall_score", "reasoning", "explanation", "issues", "suggestions"]
            for field in required_fields:
                if field not in result:
                    if field.endswith("_score") or "correctness" in field or "logic" in field or "compliance" in field or "efficiency" in field:
                        result[field] = 0.5
                    else:
                        result[field] = "Not evaluated"

            return result

        except Exception as e:
            print(f"🔍 SQL Evaluator: Exception in async evaluate_sql: {e}")
            return {
                "syntax_correctness": 0.0,
                "query_logic": 0.0,
                "schema_compliance": 0.0,
                "performance_efficiency": 0.0,
                "overall_score": 0.0,
                "explanation": f"Evaluation failed: {str(e)}",
                "issues": ["Evaluation system error"],
                "suggestions": ["Manual review required"]
            }

    def evaluate_sql_sync(self, sql: str, user_request: str, table_type: str) -> Dict[str, Any]:
        """
        Synchronous wrapper for SQL evaluation

        Args:
            sql: The generated SQL query
            user_request: Original user request
            table_type: 'rx_claims' or 'med_claims'

        Returns:
            Dictionary with evaluation scores and feedback
        """
        print(f"🔍 SQL Evaluator: Starting evaluation for {table_type}")
        try:
            loop = asyncio.get_event_loop()
            result = loop.run_until_complete(self.evaluate_sql(sql, user_request, table_type))
            print(f"🔍 SQL Evaluator: Evaluation completed, score: {result.get('overall_score', 'N/A')}")
            return result
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                result = loop.run_until_complete(self.evaluate_sql(sql, user_request, table_type))
                print(f"🔍 SQL Evaluator: Evaluation completed, score: {result.get('overall_score', 'N/A')}")
                return result
            finally:
                loop.close()


# Global instance for easy import
sql_evaluator = SQLEvaluator()


def evaluate_sql_correctness(sql: str, user_request: str, table_type: str) -> Dict[str, Any]:
    """
    Convenience function to evaluate SQL correctness

    Args:
        sql: The generated SQL query
        user_request: Original user request
        table_type: 'rx_claims' or 'med_claims'

    Returns:
        Dictionary with evaluation scores and feedback
    """
    if not os.getenv("ENABLE_EVALS", "false").lower() == "true":
        return {"evaluation_disabled": True}
    return sql_evaluator.evaluate_sql_sync(sql, user_request, table_type)