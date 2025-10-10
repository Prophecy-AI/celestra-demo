"""Test suite for Statistical Validation Tool"""

import pytest
import tempfile
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
