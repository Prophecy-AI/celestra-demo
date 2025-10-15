"""Tests for Hallucination evaluator"""
import pytest
from evals_v5.hallucination import HallucinationEvaluator


def test_hallucination_evaluator_name():
    """Test 1: Evaluator has correct name"""
    evaluator = HallucinationEvaluator()
    assert evaluator.name == "hallucination"


def test_hallucination_evaluator_prompt_template():
    """Test 2: Prompt template has required fields"""
    evaluator = HallucinationEvaluator()
    template = evaluator.prompt_template

    assert "{answer}" in template
    assert "{data}" in template
    assert "JSON" in template
    assert "hallucinations" in template


def test_hallucination_evaluator_parse_result():
    """Test 3: Parse valid JSON result"""
    evaluator = HallucinationEvaluator()

    result_text = '''
    {
      "score": 95,
      "passed": true,
      "hallucinations": [],
      "reasoning": "All claims supported by data"
    }
    '''

    result = evaluator._parse_result(result_text)

    assert result["score"] == 95
    assert result["passed"] is True
    assert result["hallucinations"] == []
    assert "reasoning" in result


def test_hallucination_evaluator_detects_issues():
    """Test 4: Parse result with detected hallucinations"""
    evaluator = HallucinationEvaluator()

    result_text = '''
    {
      "score": 40,
      "passed": false,
      "hallucinations": ["Claimed 1000 users but data shows 500", "Invented revenue figure"],
      "reasoning": "Multiple unsupported claims"
    }
    '''

    result = evaluator._parse_result(result_text)

    assert result["score"] == 40
    assert result["passed"] is False
    assert len(result["hallucinations"]) == 2
