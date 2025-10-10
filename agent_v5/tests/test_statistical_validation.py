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
