"""
Complete tool - Present final results and get feedback
"""
from typing import Dict, Any
from agent_v3.tools.base import Tool, ToolResult
from agent_v3.tools.categories import ToolCategory
from evals.hallucination_evaluator import evaluate_hallucination
from evals.answer_evaluator import evaluate_answer_relevancy
from . import prompts


class Complete(Tool):
    """Tool for presenting final results and getting feedback"""

    def __init__(self):
        super().__init__(
            name="complete",
            description="Present final results and datasets to user",
            category=ToolCategory.COMPLETION
        )

    @classmethod
    def get_orchestrator_info(cls) -> str:
        """Return tool description for orchestrator system prompt"""
        return prompts.get_orchestrator_info()

    @classmethod
    def get_system_prompt(cls, **variables) -> None:
        """Non-LLM tool - no system prompt needed"""
        return prompts.get_system_prompt(**variables)

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """Present results and get user feedback"""
        error = self.validate_parameters(parameters, ["summary", "datasets"])
        if error:
            return ToolResult(success=False, data={}, error=error)

        summary = parameters["summary"]
        dataset_names = parameters["datasets"]

        original_query = getattr(context, 'original_user_query', 'Query not available')

        supporting_data = ""
        if dataset_names:
            for name in dataset_names:
                df = context.get_dataframe(name)
                if df is not None and not df.is_empty():
                    supporting_data += f"\n{name}: {df.shape[0]} rows × {df.shape[1]} columns"

        try:
            hallucination_eval = evaluate_hallucination(summary, supporting_data, original_query)
            score = hallucination_eval.get('overall_confidence', 'N/A')
            reasoning = hallucination_eval.get('reasoning', 'No reasoning provided')
            print(f"✅ Hallucination Evaluation: {score} - {reasoning}")
        except Exception as e:
            hallucination_eval = {"error": str(e)}
            print(f"⚠️ Hallucination evaluation failed: {e}")

        try:
            answer_eval = evaluate_answer_relevancy(original_query, summary, supporting_data)
            score = answer_eval.get('overall_relevancy', 'N/A')
            reasoning = answer_eval.get('reasoning', 'No reasoning provided')
            print(f"✅ Answer Evaluation: {score} - {reasoning}")
        except Exception as e:
            answer_eval = {"error": str(e)}
            print(f"⚠️ Answer evaluation failed: {e}")

        io_handler = getattr(context, 'io_handler', None)

        def output(msg: str):
            if io_handler:
                io_handler.send_output(msg)
            else:
                print(msg)

        output(f"\n{summary}\n")

        return ToolResult(
            success=True,
            data={
                "feedback": "Analysis complete",
                "action": "end"
            }
        )
