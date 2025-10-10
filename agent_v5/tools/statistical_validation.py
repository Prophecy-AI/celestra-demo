"""
Statistical Validation Tool for Research Agent

Provides statistical validation capabilities for research quality.
"""

from typing import Dict
import numpy as np
from scipy import stats
from agent_v5.tools.base import BaseTool


class StatisticalValidationTool(BaseTool):
    """Statistical validation tool for research quality."""
    
    @property
    def name(self) -> str:
        return "StatisticalValidation"
    
    @property
    def schema(self) -> Dict:
        return {
            "name": "StatisticalValidation",
            "description": "Perform statistical validation on research data",
            "input_schema": {
                "type": "object",
                "properties": {
                    "operation": {
                        "type": "string",
                        "description": "Operation to perform",
                        "enum": ["echo", "normality_test"]
                    },
                    "data": {
                        "type": "object",
                        "description": "Input data",
                        "properties": {
                            "values": {
                                "type": "array",
                                "description": "Array of numeric values"
                            }
                        }
                    }
                },
                "required": ["operation"]
            }
        }
    
    async def execute(self, input: Dict) -> Dict:
        """Execute statistical validation operation."""
        operation = input.get("operation")
        data = input.get("data", {})
        
        if operation == "echo":
            return {
                "content": f"Echo: {data}",
                "is_error": False
            }
        
        elif operation == "normality_test":
            return self._normality_test(data)
        
        return {
            "content": f"Unknown operation: {operation}",
            "is_error": True
        }
    
    def _normality_test(self, data: Dict) -> Dict:
        """Perform Shapiro-Wilk normality test."""
        try:
            values = np.array(data.get("values", []))
            
            if len(values) < 3:
                return {
                    "content": "Need at least 3 values for normality test",
                    "is_error": True
                }
            
            statistic, p_value = stats.shapiro(values)
            is_normal = p_value > 0.05
            
            result = {
                "test": "Shapiro-Wilk",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "is_normal": is_normal,
                "interpretation": "Data appears normally distributed" if is_normal 
                                else "Data deviates from normal distribution"
            }
            
            return {
                "content": str(result),
                "is_error": False
            }
        except Exception as e:
            return {
                "content": f"Error in normality test: {str(e)}",
                "is_error": True
            }