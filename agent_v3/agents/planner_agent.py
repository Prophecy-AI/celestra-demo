"""
Planner agent for decomposing user queries into actionable steps
"""
import json
from typing import Dict, Any, List
from .base_agent import BaseAgent
from ..context import Context


class PlannerAgent(BaseAgent):
    """Agent responsible for decomposing complex queries into actionable plans"""

    def __init__(self):
        super().__init__(
            name="planner",
            description="Decomposes user queries into structured analysis plans",
            allowed_tools=["web_search", "clinical_context_search"]
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for the planner agent"""
        return """You are a specialized Planner Agent for healthcare data analysis and predictive modeling.

Your role is to decompose complex user queries into structured, actionable analysis plans.

## CORE RESPONSIBILITIES:
1. Analyze user queries for predictive modeling requirements
2. Identify required data sources and features
3. Determine analysis sequence and dependencies
4. Specify output requirements and success criteria
5. Create structured JSON plans for execution

## PLANNING FRAMEWORK:
For predictive analysis queries, decompose into:
1. **Data Requirements**: What datasets, time windows, and features are needed
2. **Feature Engineering**: What predictive features should be generated
3. **Analysis Steps**: Sequence of analytical operations
4. **Validation**: How to verify results
5. **Output Format**: How results should be presented

## OUTPUT FORMAT:
Always return a structured JSON plan with these components:

```json
{
  "query_type": "predictive_analysis|descriptive_analysis|exploratory",
  "objective": "Clear statement of what needs to be predicted/analyzed",
  "data_requirements": {
    "datasets": ["list of required datasets"],
    "time_windows": {"early_period": "1-3 months", "target_period": "12 months"},
    "filters": ["any required filters"]
  },
  "feature_engineering": {
    "feature_types": ["volume", "growth", "consistency", "behavioral"],
    "custom_features": ["any custom features needed"]
  },
  "analysis_steps": [
    {
      "step": 1,
      "action": "data_extraction",
      "description": "Extract prescribing data for analysis",
      "tools": ["text_to_sql_rx", "bigquery_sql_query"],
      "outputs": ["prescribing_dataset"]
    }
  ],
  "success_criteria": ["clear criteria for successful completion"],
  "expected_outputs": ["list of expected deliverables"]
}
```

## EXAMPLE PLANNING:
Query: "What characteristics predict high prescribers in Month 12?"

Your plan should include:
- Data extraction for Months 1-3 (early signals)
- Feature engineering for volume, growth, consistency patterns
- Trajectory classification
- Correlation analysis with Month 12 outcomes
- Ranking of predictive features

## GUIDELINES:
- Always consider both internal data (BigQuery) and external context (web search)
- Break complex analyses into logical sequential steps
- Specify clear success criteria and validation methods
- Consider data quality and availability constraints
- Plan for interpretability and actionable insights

Focus on creating comprehensive, executable plans that can be followed by other specialized agents."""

    def process(self, input_data: Dict[str, Any], context: Context, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Process user query and create structured analysis plan"""

        user_query = input_data.get("query", "")
        additional_context = input_data.get("context", {})

        # Create messages for LLM
        messages = [
            {
                "role": "user",
                "content": f"Create a detailed analysis plan for this query: {user_query}"
            }
        ]

        # Add context information if available
        if additional_context:
            context_str = json.dumps(additional_context, indent=2)
            messages.append({
                "role": "user",
                "content": f"Additional context: {context_str}"
            })

        # Add current system state
        system_context = self.format_context_for_agent(context)
        messages.append({
            "role": "user",
            "content": f"Current system state: {json.dumps(system_context, indent=2)}"
        })

        # Define JSON schema for structured output
        plan_schema = {
            "type": "object",
            "properties": {
                "query_type": {"type": "string", "enum": ["predictive_analysis", "descriptive_analysis", "exploratory"]},
                "objective": {"type": "string"},
                "data_requirements": {
                    "type": "object",
                    "properties": {
                        "datasets": {"type": "array", "items": {"type": "string"}},
                        "time_windows": {"type": "object"},
                        "filters": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "feature_engineering": {
                    "type": "object",
                    "properties": {
                        "feature_types": {"type": "array", "items": {"type": "string"}},
                        "custom_features": {"type": "array", "items": {"type": "string"}}
                    }
                },
                "analysis_steps": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "step": {"type": "integer"},
                            "action": {"type": "string"},
                            "description": {"type": "string"},
                            "tools": {"type": "array", "items": {"type": "string"}},
                            "outputs": {"type": "array", "items": {"type": "string"}}
                        }
                    }
                },
                "success_criteria": {"type": "array", "items": {"type": "string"}},
                "expected_outputs": {"type": "array", "items": {"type": "string"}}
            },
            "required": ["query_type", "objective", "data_requirements", "analysis_steps"]
        }

        try:
            # Generate structured plan
            response = self.create_structured_message(messages, plan_schema)

            # Parse the structured response
            if response and "content" in response:
                try:
                    plan = json.loads(response["content"])
                    return {
                        "success": True,
                        "plan": plan,
                        "agent": self.name,
                        "message": f"Created {len(plan.get('analysis_steps', []))} step analysis plan"
                    }
                except json.JSONDecodeError:
                    # Fallback to extracting JSON from response
                    content = response["content"]
                    start = content.find("{")
                    end = content.rfind("}") + 1
                    if start != -1 and end != -1:
                        plan_json = content[start:end]
                        plan = json.loads(plan_json)
                        return {
                            "success": True,
                            "plan": plan,
                            "agent": self.name,
                            "message": f"Created {len(plan.get('analysis_steps', []))} step analysis plan"
                        }

            return {
                "success": False,
                "error": "Failed to generate structured plan",
                "agent": self.name,
                "raw_response": response
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Planning failed: {str(e)}",
                "agent": self.name
            }

    def validate_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        """Validate that a plan is complete and executable"""
        validation_results = {
            "is_valid": True,
            "issues": [],
            "warnings": []
        }

        # Check required fields
        required_fields = ["query_type", "objective", "data_requirements", "analysis_steps"]
        for field in required_fields:
            if field not in plan:
                validation_results["is_valid"] = False
                validation_results["issues"].append(f"Missing required field: {field}")

        # Validate analysis steps
        if "analysis_steps" in plan:
            steps = plan["analysis_steps"]
            if not isinstance(steps, list) or len(steps) == 0:
                validation_results["is_valid"] = False
                validation_results["issues"].append("Analysis steps must be a non-empty list")
            else:
                # Check step sequence
                step_numbers = [step.get("step", 0) for step in steps]
                if step_numbers != list(range(1, len(steps) + 1)):
                    validation_results["warnings"].append("Steps should be numbered sequentially starting from 1")

                # Check tool availability
                for step in steps:
                    tools = step.get("tools", [])
                    for tool in tools:
                        if tool not in ["text_to_sql_rx", "text_to_sql_med", "bigquery_sql_query",
                                      "feature_engineering", "trajectory_classification", "web_search"]:
                            validation_results["warnings"].append(f"Unknown tool in step {step.get('step')}: {tool}")

        return validation_results