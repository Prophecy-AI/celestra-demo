"""
Internal evaluation systems for Agent V3
"""

# Make evaluators available at package level
try:
    from .sql_evaluator import evaluate_sql_correctness
    from .hallucination_evaluator import evaluate_hallucination
    from .retrieval_evaluator import evaluate_retrieval_relevancy
    from .answer_evaluator import evaluate_answer_relevancy

    __all__ = [
        'evaluate_sql_correctness',
        'evaluate_hallucination',
        'evaluate_retrieval_relevancy',
        'evaluate_answer_relevancy'
    ]
except ImportError as e:
    # If dependencies not available, create dummy functions
    def evaluate_sql_correctness(*args, **kwargs):
        return {"error": f"Evaluation unavailable: {e}"}

    def evaluate_hallucination(*args, **kwargs):
        return {"error": f"Evaluation unavailable: {e}"}

    def evaluate_retrieval_relevancy(*args, **kwargs):
        return {"error": f"Evaluation unavailable: {e}"}

    def evaluate_answer_relevancy(*args, **kwargs):
        return {"error": f"Evaluation unavailable: {e}"}

    __all__ = [
        'evaluate_sql_correctness',
        'evaluate_hallucination',
        'evaluate_retrieval_relevancy',
        'evaluate_answer_relevancy'
    ]