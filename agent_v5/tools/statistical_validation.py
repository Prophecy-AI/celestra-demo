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
                        "enum": ["echo", "normality_test", "sample_size_check", "t_test", "mann_whitney", "cohen_d"]
                    },
                    "data": {
                        "type": "object",
                        "description": "Input data",
                        "properties": {
                            "values": {
                                "type": "array",
                                "description": "Array of numeric values"
                            },
                            "test_type": {
                                "type": "string",
                                "description": "Type of statistical test planned"
                            },
                            "group1": {
                                "type": "array",
                                "description": "First group of values"
                            },
                            "group2": {
                                "type": "array", 
                                "description": "Second group of values"
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
        
        elif operation == "sample_size_check":
            return self._sample_size_check(data)
        
        elif operation == "t_test":
            return self._t_test(data)
        
        elif operation == "mann_whitney":
            return self._mann_whitney(data)
        
        elif operation == "cohen_d":
            return self._cohen_d(data)
        
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
    
    def _sample_size_check(self, data: Dict) -> Dict:
        """Check if sample size is adequate for planned test."""
        try:
            values = data.get("values", [])
            test_type = data.get("test_type", "parametric")
            n = len(values) if isinstance(values, list) else values
            
            # Define minimum sample size requirements
            requirements = {
                "parametric": 30,
                "t-test": 30,
                "anova": 20,  # per group
                "correlation": 10,
                "regression": 50,
                "chi-square": 5,  # per cell
                "non-parametric": 10
            }
            
            min_required = requirements.get(test_type, 30)
            is_adequate = n >= min_required
            
            result = {
                "sample_size": n,
                "test_type": test_type,
                "minimum_required": min_required,
                "is_adequate": is_adequate,
                "interpretation": f"Sample size (n={n}) is {'adequate' if is_adequate else 'too small'} for {test_type} test (minimum: {min_required})"
            }
            
            return {
                "content": str(result),
                "is_error": False
            }
        except Exception as e:
            return {
                "content": f"Error in sample size check: {str(e)}",
                "is_error": True
            }
    
    def _t_test(self, data: Dict) -> Dict:
        """Perform two-sample t-test."""
        try:
            group1 = np.array(data.get("group1", []))
            group2 = np.array(data.get("group2", []))
            
            if len(group1) < 2 or len(group2) < 2:
                return {
                    "content": "Each group needs at least 2 values",
                    "is_error": True
                }
            
            statistic, p_value = stats.ttest_ind(group1, group2)
            significant = p_value < 0.05
            
            result = {
                "test": "Independent t-test",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "significant": significant,
                "interpretation": f"Groups are {'significantly different' if significant else 'not significantly different'} (p={p_value:.4f})"
            }
            
            return {
                "content": str(result),
                "is_error": False
            }
        except Exception as e:
            return {
                "content": f"Error in t-test: {str(e)}",
                "is_error": True
            }
    
    def _mann_whitney(self, data: Dict) -> Dict:
        """Perform Mann-Whitney U test (non-parametric alternative to t-test)."""
        try:
            group1 = np.array(data.get("group1", []))
            group2 = np.array(data.get("group2", []))
            
            if len(group1) < 2 or len(group2) < 2:
                return {
                    "content": "Each group needs at least 2 values",
                    "is_error": True
                }
            
            # Mann-Whitney U test
            statistic, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
            significant = p_value < 0.05
            
            result = {
                "test": "Mann-Whitney U",
                "statistic": float(statistic),
                "p_value": float(p_value),
                "significant": significant,
                "interpretation": f"Groups are {'significantly different' if significant else 'not significantly different'} (p={p_value:.4f})",
                "note": "Non-parametric test used (no normality assumption)"
            }
            
            return {
                "content": str(result),
                "is_error": False
            }
        except Exception as e:
            return {
                "content": f"Error in Mann-Whitney U test: {str(e)}",
                "is_error": True
            }
    
    def _cohen_d(self, data: Dict) -> Dict:
        """Calculate Cohen's d effect size for two groups."""
        try:
            group1 = np.array(data.get("group1", []))
            group2 = np.array(data.get("group2", []))
            
            if len(group1) < 2 or len(group2) < 2:
                return {
                    "content": "Each group needs at least 2 values",
                    "is_error": True
                }
            
            # Calculate means and standard deviations
            mean1, mean2 = np.mean(group1), np.mean(group2)
            std1, std2 = np.std(group1, ddof=1), np.std(group2, ddof=1)
            n1, n2 = len(group1), len(group2)
            
            # Calculate pooled standard deviation
            pooled_std = np.sqrt(((n1 - 1) * std1**2 + (n2 - 1) * std2**2) / (n1 + n2 - 2))
            
            # Calculate Cohen's d
            d = (mean1 - mean2) / pooled_std if pooled_std > 0 else 0
            
            # Interpret effect size
            abs_d = abs(d)
            if abs_d < 0.2:
                interpretation = "negligible"
            elif abs_d < 0.5:
                interpretation = "small"
            elif abs_d < 0.8:
                interpretation = "medium"
            else:
                interpretation = "large"
            
            result = {
                "cohen_d": float(d),
                "interpretation": f"{interpretation} effect size",
                "mean1": float(mean1),
                "mean2": float(mean2),
                "pooled_std": float(pooled_std),
                "direction": "group1 > group2" if d > 0 else "group2 > group1"
            }
            
            return {
                "content": str(result),
                "is_error": False
            }
        except Exception as e:
            return {
                "content": f"Error in Cohen's d calculation: {str(e)}",
                "is_error": True
            }