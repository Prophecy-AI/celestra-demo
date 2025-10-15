"""Tests for SQL evaluator"""
import pytest
from evals_v5.sql import SQLEvaluator


def test_sql_evaluator_name():
    """Test 1: Evaluator has correct name"""
    evaluator = SQLEvaluator()
    assert evaluator.name == "sql"


def test_sql_evaluator_prompt_template():
    """Test 2: Prompt template has required fields"""
    evaluator = SQLEvaluator()
    template = evaluator.prompt_template

    assert "{sql}" in template
    assert "{context}" in template
    assert "JSON" in template


def test_sql_evaluator_parse_result():
    """Test 3: Parse valid JSON result"""
    evaluator = SQLEvaluator()

    result_text = '''
    {
      "score": 85,
      "passed": true,
      "issues": ["No index on user_id"],
      "reasoning": "Query is syntactically correct but could use index"
    }
    '''

    result = evaluator._parse_result(result_text)

    assert result["score"] == 85
    assert result["passed"] is True
    assert "No index on user_id" in result["issues"]
    assert "reasoning" in result
