"""Test suite for Statistical Validation Tool"""

import pytest
import tempfile
import numpy as np
from agent_v5.tools.statistical_validation import StatisticalValidationTool


@pytest.mark.asyncio
async def test_base_structure():
    """Test that the base tool structure works."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = StatisticalValidationTool(tmpdir)
        
        # Test basic properties
        assert tool.name == "StatisticalValidation"
        assert "StatisticalValidation" in tool.schema["name"]
        
        # Test echo operation
        result = await tool.execute({
            "operation": "echo",
            "data": {"test": "value"}
        })
        
        assert not result["is_error"]
        assert "Echo" in result["content"]


@pytest.mark.asyncio
async def test_normality_test():
    """Test Shapiro-Wilk normality test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = StatisticalValidationTool(tmpdir)
        
        # Test with normal data
        np.random.seed(42)
        normal_data = np.random.normal(0, 1, 100).tolist()
        
        result = await tool.execute({
            "operation": "normality_test",
            "data": {"values": normal_data}
        })
        
        assert not result["is_error"]
        assert "Shapiro-Wilk" in result["content"]
        assert "p_value" in result["content"]


@pytest.mark.asyncio
async def test_sample_size_check():
    """Test sample size validation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = StatisticalValidationTool(tmpdir)
        
        # Test with adequate sample size
        result = await tool.execute({
            "operation": "sample_size_check",
            "data": {
                "values": list(range(50)),
                "test_type": "t-test"
            }
        })
        
        assert not result["is_error"]
        assert "adequate" in result["content"]
        
        # Test with inadequate sample size
        result = await tool.execute({
            "operation": "sample_size_check", 
            "data": {
                "values": [1, 2, 3],
                "test_type": "regression"
            }
        })
        
        assert not result["is_error"]
        assert "too small" in result["content"]


@pytest.mark.asyncio
async def test_t_test():
    """Test two-sample t-test."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = StatisticalValidationTool(tmpdir)
        
        # Create two groups with different means
        np.random.seed(42)
        group1 = np.random.normal(0, 1, 30).tolist()
        group2 = np.random.normal(2, 1, 30).tolist()
        
        result = await tool.execute({
            "operation": "t_test",
            "data": {
                "group1": group1,
                "group2": group2
            }
        })
        
        assert not result["is_error"]
        assert "t-test" in result["content"]
        assert "p_value" in result["content"]


@pytest.mark.asyncio
async def test_mann_whitney():
    """Test Mann-Whitney U test (non-parametric)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = StatisticalValidationTool(tmpdir)
        
        # Create two groups with non-normal data (outliers)
        group1 = [1, 2, 2, 3, 4, 100]  # Outlier in group1
        group2 = [5, 6, 7, 8, 9, 10]
        
        result = await tool.execute({
            "operation": "mann_whitney",
            "data": {
                "group1": group1,
                "group2": group2
            }
        })
        
        assert not result["is_error"]
        assert "Mann-Whitney" in result["content"]
        assert "Non-parametric" in result["content"]


@pytest.mark.asyncio
async def test_cohen_d():
    """Test Cohen's d effect size calculation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tool = StatisticalValidationTool(tmpdir)
        
        # Create two groups with known effect size
        # Mean difference = 2, pooled SD ≈ 1, so d ≈ 2 (large effect)
        group1 = [1, 2, 3, 4, 5]
        group2 = [3, 4, 5, 6, 7]
        
        result = await tool.execute({
            "operation": "cohen_d",
            "data": {
                "group1": group1,
                "group2": group2
            }
        })
        
        assert not result["is_error"]
        assert "cohen_d" in result["content"]
        assert "effect size" in result["content"]
        
        # With these values, we expect a negative Cohen's d (group2 > group1)
        assert "group2 > group1" in result["content"]
