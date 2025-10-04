"""
Holistic Critic Agent for Agent V3
Evaluates entire conversation flow using existing eval rubrics
Runs BEFORE returning results to user
"""
import os
import asyncio
from typing import Dict, Any, Optional, List
import json
from pydantic import BaseModel, Field
from dotenv import load_dotenv
import openai

load_dotenv()

# Import existing evaluators
import sys
from pathlib import Path
# Add evals directory to path
evals_path = Path(__file__).parent.parent.parent / "evals"
sys.path.insert(0, str(evals_path))

from answer_evaluator import AnswerEvaluator
from hallucination_evaluator import HallucinationEvaluator
from sql_evaluator import SQLEvaluator
from retrieval_evaluator import RetrievalEvaluator


class HolisticCritiqueSchema(BaseModel):
    """Structured output schema for holistic critique"""

    # Overall evaluation
    overall_quality_score: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    requires_revision: bool = Field(description="Whether the workflow needs revision")

    # Dimension scores (aggregated from rubrics)
    answer_quality: float = Field(ge=0.0, le=1.0, description="Answer relevancy and completeness")
    factual_accuracy: float = Field(ge=0.0, le=1.0, description="Factual correctness and data consistency")
    sql_quality: float = Field(ge=0.0, le=1.0, description="SQL correctness and efficiency")
    retrieval_quality: float = Field(ge=0.0, le=1.0, description="Data retrieval relevancy")
    workflow_efficiency: float = Field(ge=0.0, le=1.0, description="Tool execution efficiency")
    clinical_context: float = Field(ge=0.0, le=1.0, description="Use of clinical/external context")

    # Detailed findings
    strengths: List[str] = Field(description="What the workflow did well")
    critical_issues: List[str] = Field(description="Critical problems requiring revision")
    improvement_suggestions: List[str] = Field(description="Specific improvement recommendations")
    missing_elements: List[str] = Field(description="Key elements not addressed")

    # Error analysis
    error_recovery_quality: float = Field(ge=0.0, le=1.0, description="How well errors were handled")
    error_summary: List[str] = Field(description="Summary of errors encountered")

    # Final summary
    critique_summary: str = Field(description="2-3 sentence executive summary of critique")
    revision_priority: str = Field(description="Priority level: critical, high, medium, low, none")


class HolisticCriticAgent:
    """
    Holistic Critic Agent that evaluates entire conversation flow.
    Uses existing eval rubrics to assess multiple dimensions.
    Runs BEFORE returning results to user.
    """

    def __init__(self):
        self.name = "HolisticCriticAgent"
        self.description = "Evaluates entire conversation flow for quality assurance"

        # Initialize OpenAI client with GPT-4o for comprehensive critique
        self.client = openai.AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = "gpt-4o"  # Use GPT-4o for high-quality evaluation

        # Initialize existing evaluators
        self.answer_evaluator = AnswerEvaluator()
        self.hallucination_evaluator = HallucinationEvaluator()
        self.sql_evaluator = SQLEvaluator()
        self.retrieval_evaluator = RetrievalEvaluator()

        self.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        """Build comprehensive holistic evaluation prompt"""
        return """You are an expert quality assurance evaluator for healthcare data analysis workflows.

Your task is to perform a HOLISTIC evaluation of the ENTIRE conversation flow, not just the final output.

EVALUATION SCOPE:
- Original user query and intent
- All tool executions and their parameters
- SQL queries generated and executed
- Data retrieved and its relevance
- Error handling and recovery attempts
- Use of external context (web search, clinical knowledge)
- Final answer quality and completeness
- Overall workflow efficiency

COMPREHENSIVE ASSESSMENT DIMENSIONS:

1. ANSWER QUALITY (0.0-1.0):
   - Does the final response address the user's query?
   - Is it complete, clear, and actionable?
   - Are insights properly explained?

2. FACTUAL ACCURACY (0.0-1.0):
   - Are medical terms and concepts correct?
   - Are statistical interpretations sound?
   - Are claims supported by data?

3. SQL QUALITY (0.0-1.0):
   - Are SQL queries syntactically correct?
   - Do they efficiently retrieve needed data?
   - Are DATE handling patterns correct (no EXTRACT(MONTH FROM DATE_DIFF(...)))?

4. RETRIEVAL QUALITY (0.0-1.0):
   - Is retrieved data relevant to the query?
   - Is data scope appropriate?
   - Are all needed dimensions captured?

5. WORKFLOW EFFICIENCY (0.0-1.0):
   - Was the right sequence of tools used?
   - Were unnecessary steps avoided?
   - Did errors get resolved efficiently?

6. CLINICAL CONTEXT (0.0-1.0):
   - Was external clinical knowledge used when needed?
   - Were web searches performed for domain context?
   - Is pharmaceutical expertise evident?

CRITICAL ISSUES REQUIRING REVISION:
- SQL errors repeated without resolution
- Missing critical data for answering the query
- Factual hallucinations or inaccuracies
- Complete failure to address user's question
- No use of web search when clinical context needed
- Pharmaceutical predictors missing for predictive queries

WORKFLOW PATTERNS TO CHECK:
- Predictive analysis queries should use multi-agent workflow
- Clinical context should be searched via Tavily
- SQL DATE_DIFF should never be wrapped in EXTRACT()
- Feature engineering should include pharmaceutical-specific predictors
- Errors should trigger alternative approaches

REVISION PRIORITY LEVELS:
- critical: Must revise (factual errors, missing data, wrong answer)
- high: Should revise (incomplete analysis, missing context)
- medium: Could improve (efficiency issues, minor gaps)
- low: Optional improvements (style, clarity)
- none: No revision needed

Your evaluation should be comprehensive, evidence-based, and actionable."""

    async def evaluate_workflow(self, execution_log: Dict[str, Any]) -> Dict[str, Any]:
        """
        Perform holistic evaluation of entire workflow.

        Args:
            execution_log: Full execution log from context.get_full_execution_log()

        Returns:
            Comprehensive critique with revision recommendations
        """

        # Extract key components from execution log
        original_query = execution_log.get("original_query", "")
        tool_executions = execution_log.get("tool_executions", [])
        errors = execution_log.get("errors", [])
        datasets = execution_log.get("datasets", [])
        metrics = execution_log.get("metrics", {})
        conversation_history = execution_log.get("conversation_history", [])

        # Run existing evaluators in parallel
        eval_results = await self._run_evaluators(
            original_query, tool_executions, datasets, conversation_history
        )

        # Perform comprehensive holistic analysis
        holistic_critique = await self._perform_holistic_analysis(
            execution_log, eval_results
        )

        return holistic_critique

    async def _run_evaluators(
        self,
        original_query: str,
        tool_executions: List[Dict[str, Any]],
        datasets: List[Dict[str, Any]],
        conversation_history: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Run existing evaluators on workflow components"""

        results = {
            "answer_eval": None,
            "hallucination_eval": None,
            "sql_eval": [],
            "retrieval_eval": []
        }

        # Extract final answer from conversation
        final_answer = ""
        for msg in reversed(conversation_history):
            if msg.get("role") == "assistant" and "Tool:" not in msg.get("content", ""):
                final_answer = msg.get("content", "")
                break

        # Evaluate answer quality
        if final_answer and original_query:
            try:
                results["answer_eval"] = await self.answer_evaluator.evaluate_answer(
                    user_question=original_query,
                    agent_answer=final_answer
                )
            except Exception as e:
                print(f"Answer evaluation error: {e}")

        # Evaluate hallucination risk
        if final_answer:
            try:
                dataset_summary = json.dumps(datasets, default=str)[:1000]
                results["hallucination_eval"] = await self.hallucination_evaluator.evaluate_response(
                    response=final_answer,
                    query_data=dataset_summary,
                    user_question=original_query
                )
            except Exception as e:
                print(f"Hallucination evaluation error: {e}")

        # Evaluate SQL queries
        for exec in tool_executions:
            if "sql" in exec.get("tool_name", "").lower():
                sql_query = exec.get("parameters", {}).get("query", "")
                if sql_query:
                    try:
                        sql_eval = await self.sql_evaluator.evaluate_sql(
                            sql=sql_query,
                            user_request=original_query,
                            table_type="rx_claims"
                        )
                        results["sql_eval"].append(sql_eval)
                    except Exception as e:
                        print(f"SQL evaluation error: {e}")

        # Evaluate data retrieval
        if datasets and original_query:
            try:
                retrieval_eval = await self.retrieval_evaluator.evaluate_retrieval(
                    user_query=original_query,
                    retrieved_data=datasets
                )
                results["retrieval_eval"].append(retrieval_eval)
            except Exception as e:
                print(f"Retrieval evaluation error: {e}")

        return results

    async def _perform_holistic_analysis(
        self,
        execution_log: Dict[str, Any],
        eval_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Perform comprehensive holistic analysis using GPT-4o"""

        # Build comprehensive evaluation prompt
        evaluation_prompt = self._build_evaluation_prompt(execution_log, eval_results)

        try:
            # Use GPT-4o for holistic evaluation
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": evaluation_prompt}
                ],
                temperature=0.3,
                response_format={"type": "json_object"}
            )

            critique = json.loads(response.choices[0].message.content)

            # Add metadata
            critique["evaluator"] = self.name
            critique["model"] = self.model
            critique["individual_evaluations"] = eval_results

            return critique

        except Exception as e:
            print(f"Holistic analysis error: {e}")
            # Return fallback critique
            return self._create_fallback_critique(execution_log, eval_results)

    def _build_evaluation_prompt(
        self,
        execution_log: Dict[str, Any],
        eval_results: Dict[str, Any]
    ) -> str:
        """Build comprehensive evaluation prompt"""

        original_query = execution_log.get("original_query", "N/A")
        tool_executions = execution_log.get("tool_executions", [])
        errors = execution_log.get("errors", [])
        metrics = execution_log.get("metrics", {})

        prompt = f"""HOLISTIC WORKFLOW EVALUATION REQUEST

ORIGINAL USER QUERY:
{original_query}

EXECUTION METRICS:
- Total tools executed: {metrics.get('total_tools_executed', 0)}
- Successful tools: {metrics.get('successful_tools', 0)}
- Failed tools: {metrics.get('failed_tools', 0)}
- Datasets created: {metrics.get('datasets_created', 0)}
- Recursion depth: {execution_log.get('recursion_depth', 0)}
- Duration: {execution_log.get('duration_seconds', 0):.2f} seconds

TOOL EXECUTION SEQUENCE:
"""

        for i, exec in enumerate(tool_executions[:15], 1):  # Limit to 15 most recent
            status = "✓" if exec.get("success") else "✗"
            prompt += f"{i}. {status} {exec.get('tool_name')} "
            if exec.get("error"):
                prompt += f"[ERROR: {exec.get('error')[:100]}]"
            prompt += "\n"

        if len(tool_executions) > 15:
            prompt += f"... and {len(tool_executions) - 15} more executions\n"

        prompt += f"\nERRORS ENCOUNTERED: {len(errors)}\n"
        for error in errors[:5]:
            prompt += f"- {error.get('tool_name')}: {error.get('error_message', '')[:100]}\n"

        prompt += "\nINDIVIDUAL EVALUATOR RESULTS:\n"

        # Add answer evaluation results
        if eval_results.get("answer_eval"):
            answer_eval = eval_results["answer_eval"]
            prompt += f"\nANSWER QUALITY EVALUATION:\n"
            prompt += f"- Overall relevancy: {answer_eval.get('overall_relevancy', 'N/A')}\n"
            prompt += f"- Reasoning: {answer_eval.get('reasoning', 'N/A')}\n"

        # Add hallucination evaluation results
        if eval_results.get("hallucination_eval"):
            hall_eval = eval_results["hallucination_eval"]
            prompt += f"\nHALLUCINATION RISK EVALUATION:\n"
            prompt += f"- Hallucination risk: {hall_eval.get('hallucination_risk', 'N/A')}\n"
            prompt += f"- Overall confidence: {hall_eval.get('overall_confidence', 'N/A')}\n"

        # Add SQL evaluation results
        if eval_results.get("sql_eval"):
            prompt += f"\nSQL QUALITY EVALUATION ({len(eval_results['sql_eval'])} queries):\n"
            for sql_eval in eval_results["sql_eval"][:3]:
                prompt += f"- Overall score: {sql_eval.get('overall_score', 'N/A')}\n"
                if sql_eval.get("issues"):
                    prompt += f"  Issues: {', '.join(sql_eval['issues'][:3])}\n"

        prompt += """

REQUIRED OUTPUT FORMAT (JSON):
{
  "overall_quality_score": 0.85,
  "requires_revision": false,
  "answer_quality": 0.87,
  "factual_accuracy": 0.92,
  "sql_quality": 0.83,
  "retrieval_quality": 0.89,
  "workflow_efficiency": 0.78,
  "clinical_context": 0.65,
  "strengths": ["Specific strengths observed"],
  "critical_issues": ["Critical problems if any"],
  "improvement_suggestions": ["Specific actionable recommendations"],
  "missing_elements": ["Key missing elements"],
  "error_recovery_quality": 0.80,
  "error_summary": ["Summary of error patterns"],
  "critique_summary": "2-3 sentence executive summary",
  "revision_priority": "none|low|medium|high|critical"
}

Provide comprehensive, evidence-based evaluation in JSON format ONLY."""

        return prompt

    def _create_fallback_critique(
        self,
        execution_log: Dict[str, Any],
        eval_results: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Create fallback critique when GPT-4o evaluation fails"""

        metrics = execution_log.get("metrics", {})
        errors = execution_log.get("errors", [])

        # Calculate basic scores
        success_rate = metrics.get("successful_tools", 0) / max(metrics.get("total_tools_executed", 1), 1)
        has_datasets = metrics.get("datasets_created", 0) > 0
        has_critical_errors = len(errors) > 3

        return {
            "overall_quality_score": success_rate * 0.7,
            "requires_revision": has_critical_errors or not has_datasets,
            "answer_quality": 0.5,
            "factual_accuracy": 0.5,
            "sql_quality": success_rate,
            "retrieval_quality": 0.7 if has_datasets else 0.3,
            "workflow_efficiency": success_rate,
            "clinical_context": 0.5,
            "strengths": ["Executed workflow"],
            "critical_issues": ["Evaluation failed - manual review needed"] + [e.get("error_message", "")[:100] for e in errors[:3]],
            "improvement_suggestions": ["Review errors", "Check tool selection"],
            "missing_elements": ["Full evaluation unavailable"],
            "error_recovery_quality": 0.5,
            "error_summary": [f"{len(errors)} errors encountered"],
            "critique_summary": f"Fallback evaluation: {len(errors)} errors, {metrics.get('datasets_created', 0)} datasets created. Manual review recommended.",
            "revision_priority": "high" if has_critical_errors else "medium",
            "evaluator": "HolisticCriticAgent (fallback)",
            "model": "fallback"
        }
