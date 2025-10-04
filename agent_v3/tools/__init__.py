"""
Tools package for agent_v3
"""
from .sql_generation import TextToSQLRx, TextToSQLMed, TextToSQLProvidersBio, TextToSQLProviderPayments
from .sql_execution import BigQuerySQLQuery
from .io_tools import Communicate, Complete
from .web_search import WebSearchTool, ClinicalContextSearchTool
from .feature_engineering import FeatureEngineeringTool, TrajectoryClassificationTool
from .pharmaceutical_features import PharmaceuticalFeatureEngineeringTool
from .predictive_analysis import PredictiveAnalysisTool
from .base import Tool, ToolResult

# Initialize all tools
def get_all_tools():
    """Return dictionary of all available tools"""
    tools = {
        # Original SQL and communication tools
        "text_to_sql_rx": TextToSQLRx(),
        "text_to_sql_med": TextToSQLMed(),
        "text_to_sql_provider_payments": TextToSQLProviderPayments(),
        "text_to_sql_providers_bio": TextToSQLProvidersBio(),
        "bigquery_sql_query": BigQuerySQLQuery(),
        "communicate": Communicate(),
        "complete": Complete(),

        # New predictive analytics tools
        "web_search": WebSearchTool(),
        "clinical_context_search": ClinicalContextSearchTool(),
        "feature_engineering": FeatureEngineeringTool(),
        "pharmaceutical_feature_engineering": PharmaceuticalFeatureEngineeringTool(),
        "trajectory_classification": TrajectoryClassificationTool(),
        "predictive_analysis": PredictiveAnalysisTool()
    }
    return tools

def get_core_tools():
    """Return dictionary of core tools (original functionality)"""
    tools = {
        "text_to_sql_rx": TextToSQLRx(),
        "text_to_sql_med": TextToSQLMed(),
        "text_to_sql_provider_payments": TextToSQLProviderPayments(),
        "text_to_sql_providers_bio": TextToSQLProvidersBio(),
        "bigquery_sql_query": BigQuerySQLQuery(),
        "communicate": Communicate(),
        "complete": Complete()
    }
    return tools

def get_predictive_tools():
    """Return dictionary of predictive analytics tools only"""
    tools = {
        "web_search": WebSearchTool(),
        "clinical_context_search": ClinicalContextSearchTool(),
        "feature_engineering": FeatureEngineeringTool(),
        "pharmaceutical_feature_engineering": PharmaceuticalFeatureEngineeringTool(),
        "trajectory_classification": TrajectoryClassificationTool(),
        "predictive_analysis": PredictiveAnalysisTool()
    }
    return tools

__all__ = [
    # Original tools
    "TextToSQLRx",
    "TextToSQLMed",
    "TextToSQLProviderPayments",
    "TextToSQLProvidersBio",
    "BigQuerySQLQuery",
    "Communicate",
    "Complete",

    # New predictive tools
    "WebSearchTool",
    "ClinicalContextSearchTool",
    "FeatureEngineeringTool",
    "PharmaceuticalFeatureEngineeringTool",
    "TrajectoryClassificationTool",
    "PredictiveAnalysisTool",

    # Base classes and utilities
    "Tool",
    "ToolResult",
    "get_all_tools",
    "get_core_tools",
    "get_predictive_tools"
]