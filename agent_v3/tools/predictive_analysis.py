"""
Predictive analysis tool that orchestrates multi-agent workflows for prescriber prediction
"""
import json
from typing import Dict, Any, List
from .base import Tool, ToolResult
from ..agents import PlannerAgent, RetrieverAgent, AnswererAgent, CriticAgent


class PredictiveAnalysisTool(Tool):
    """Tool for running end-to-end predictive analysis workflows using specialized agents"""

    def __init__(self):
        super().__init__(
            name="predictive_analysis",
            description="Execute comprehensive predictive analysis using multi-agent workflow"
        )

        # Initialize specialized agents
        self.planner = PlannerAgent()
        self.retriever = RetrieverAgent()
        self.answerer = AnswererAgent()
        self.critic = CriticAgent()

    def execute(self, parameters: Dict[str, Any], context: Any) -> ToolResult:
        """
        Execute multi-agent predictive analysis workflow

        Parameters:
        - query: The predictive analysis question
        - workflow_type: Type of workflow ('full', 'planning_only', 'execution_only')
        - target_features: Specific features to focus on (optional)
        - validation_level: Level of validation ('basic', 'standard', 'comprehensive')
        """
        # Validate required parameters
        validation_error = self.validate_parameters(parameters, ["query"])
        if validation_error:
            return ToolResult(success=False, data={}, error=validation_error)

        query = parameters["query"]
        workflow_type = parameters.get("workflow_type", "full")
        target_features = parameters.get("target_features", [])
        validation_level = parameters.get("validation_level", "standard")

        try:
            workflow_results = {
                "query": query,
                "workflow_type": workflow_type,
                "stages_completed": [],
                "results": {}
            }

            # Stage 1: Planning
            if workflow_type in ["full", "planning_only"]:
                planning_result = self._execute_planning_stage(query, target_features, context)
                workflow_results["stages_completed"].append("planning")
                workflow_results["results"]["planning"] = planning_result

                if not planning_result["success"]:
                    return ToolResult(
                        success=False,
                        data=workflow_results,
                        error=f"Planning stage failed: {planning_result.get('error')}"
                    )

                # Stop here if planning only
                if workflow_type == "planning_only":
                    return ToolResult(
                        success=True,
                        data={
                            **workflow_results,
                            "message": "Planning stage completed successfully",
                            "plan": planning_result.get("plan", {})
                        }
                    )

            # Stage 2: Data Retrieval and Context Gathering
            if workflow_type in ["full", "execution_only"]:
                retrieval_result = self._execute_retrieval_stage(query, context)
                workflow_results["stages_completed"].append("retrieval")
                workflow_results["results"]["retrieval"] = retrieval_result

            # Stage 3: Feature Engineering and Analysis
            if workflow_type in ["full", "execution_only"]:
                analysis_result = self._execute_analysis_stage(query, target_features, context)
                workflow_results["stages_completed"].append("analysis")
                workflow_results["results"]["analysis"] = analysis_result

            # Stage 4: Answer Generation
            if workflow_type in ["full", "execution_only"]:
                answering_result = self._execute_answering_stage(
                    query, workflow_results["results"], context
                )
                workflow_results["stages_completed"].append("answering")
                workflow_results["results"]["answering"] = answering_result

            # Stage 5: Quality Validation
            if validation_level in ["standard", "comprehensive"] and workflow_type in ["full", "execution_only"]:
                validation_result = self._execute_validation_stage(
                    workflow_results["results"], validation_level, context
                )
                workflow_results["stages_completed"].append("validation")
                workflow_results["results"]["validation"] = validation_result

                # Handle revision if required
                if validation_result.get("revision_required"):
                    revision_result = self._handle_revision(workflow_results["results"], context)
                    workflow_results["stages_completed"].append("revision")
                    workflow_results["results"]["revision"] = revision_result

            return ToolResult(
                success=True,
                data={
                    **workflow_results,
                    "message": f"Predictive analysis completed with {len(workflow_results['stages_completed'])} stages",
                    "final_output": workflow_results["results"].get("answering", {}).get("reason_card", {})
                }
            )

        except Exception as e:
            return ToolResult(
                success=False,
                data={},
                error=f"Predictive analysis workflow failed: {str(e)}"
            )

    def _execute_planning_stage(self, query: str, target_features: List[str], context: Any) -> Dict[str, Any]:
        """Execute planning stage using PlannerAgent"""

        try:
            planning_input = {
                "query": query,
                "context": {
                    "target_features": target_features,
                    "available_datasets": list(context.get_all_datasets().keys()),
                    "previous_analyses": self._get_previous_analysis_context(context)
                }
            }

            # Get available tools for planning
            available_tools = self._get_available_tools_for_agent("planner", context)

            # Execute planning
            planning_result = self.planner.process(planning_input, context, available_tools)

            if planning_result["success"]:
                # Validate the plan
                plan_validation = self.planner.validate_plan(planning_result["plan"])
                planning_result["validation"] = plan_validation

                # Store plan in context for later stages
                context.add_metadata("analysis_plan", planning_result["plan"])

            return planning_result

        except Exception as e:
            return {
                "success": False,
                "error": f"Planning stage error: {str(e)}"
            }

    def _execute_retrieval_stage(self, query: str, context: Any) -> Dict[str, Any]:
        """Execute retrieval stage using RetrieverAgent"""

        try:
            # Get analysis plan from context
            analysis_plan = context.get_metadata("analysis_plan", {})

            # Determine what to retrieve based on plan
            retrieval_requests = []

            # Always retrieve clinical context if drug mentioned
            if any(keyword in query.lower() for keyword in ["drug", "medication", "prescription"]):
                drug_name = self._extract_drug_name(query)
                if drug_name:
                    retrieval_requests.append({
                        "type": "clinical_context",
                        "drug_name": drug_name,
                        "request": f"Clinical context for {drug_name}"
                    })

            # Retrieve thresholds for predictive modeling
            retrieval_requests.append({
                "type": "thresholds",
                "request": "Healthcare prescriber prediction thresholds and benchmarks"
            })

            # Retrieve feature specifications
            feature_types = analysis_plan.get("feature_engineering", {}).get("feature_types", [])
            if feature_types:
                retrieval_requests.append({
                    "type": "specifications",
                    "request": f"Feature engineering specifications for {', '.join(feature_types)}"
                })

            # Execute retrievals
            available_tools = self._get_available_tools_for_agent("retriever", context)
            consolidated_results = {
                "success": True,
                "retrievals": [],
                "consolidated_facts": [],
                "error": None
            }

            for retrieval_request in retrieval_requests:
                try:
                    retrieval_result = self.retriever.process(retrieval_request, context, available_tools)
                    consolidated_results["retrievals"].append(retrieval_result)

                    if retrieval_result.get("success") and retrieval_result.get("retrieval_results"):
                        facts = retrieval_result["retrieval_results"].get("consolidated_facts", [])
                        consolidated_results["consolidated_facts"].extend(facts)

                except Exception as e:
                    consolidated_results["retrievals"].append({
                        "success": False,
                        "error": str(e),
                        "request": retrieval_request
                    })

            # Store consolidated facts for later stages
            context.add_metadata("retrieved_facts", consolidated_results)

            return consolidated_results

        except Exception as e:
            return {
                "success": False,
                "error": f"Retrieval stage error: {str(e)}"
            }

    def _execute_analysis_stage(self, query: str, target_features: List[str], context: Any) -> Dict[str, Any]:
        """Execute analysis stage using feature engineering and ML tools"""

        try:
            analysis_results = {
                "success": True,
                "feature_engineering": {},
                "trajectory_classification": {},
                "prediction_results": {},
                "error": None
            }

            # Get analysis plan
            analysis_plan = context.get_metadata("analysis_plan", {})
            analysis_steps = analysis_plan.get("analysis_steps", [])

            # Execute planned analysis steps
            for step in analysis_steps:
                step_action = step.get("action")
                step_tools = step.get("tools", [])

                if step_action == "feature_engineering" and "feature_engineering" in step_tools:
                    # Execute feature engineering
                    datasets = list(context.get_all_datasets().keys())
                    if datasets:
                        fe_result = self._execute_feature_engineering(datasets[0], target_features, context)
                        analysis_results["feature_engineering"] = fe_result

                elif step_action == "trajectory_classification" and "trajectory_classification" in step_tools:
                    # Execute trajectory classification
                    features_dataset = analysis_results.get("feature_engineering", {}).get("features_dataset")
                    if features_dataset:
                        tc_result = self._execute_trajectory_classification(features_dataset, context)
                        analysis_results["trajectory_classification"] = tc_result

                elif step_action == "prediction_modeling":
                    # Execute prediction modeling (simplified for demo)
                    prediction_result = self._execute_prediction_modeling(context)
                    analysis_results["prediction_results"] = prediction_result

            return analysis_results

        except Exception as e:
            return {
                "success": False,
                "error": f"Analysis stage error: {str(e)}"
            }

    def _execute_answering_stage(self, query: str, workflow_results: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Execute answering stage using AnswererAgent"""

        try:
            # Prepare input for answerer
            answering_input = {
                "analysis_results": workflow_results.get("analysis", {}),
                "retrieved_facts": context.get_metadata("retrieved_facts", {}),
                "query_context": query
            }

            # Get available tools (answerer typically doesn't use external tools)
            available_tools = self._get_available_tools_for_agent("answerer", context)

            # Execute answer generation
            answering_result = self.answerer.process(answering_input, context, available_tools)

            # Store reason card in context for validation
            if answering_result.get("success") and answering_result.get("reason_card"):
                context.add_metadata("reason_card", answering_result["reason_card"])

            return answering_result

        except Exception as e:
            return {
                "success": False,
                "error": f"Answering stage error: {str(e)}"
            }

    def _execute_validation_stage(self, workflow_results: Dict[str, Any], validation_level: str, context: Any) -> Dict[str, Any]:
        """Execute validation stage using CriticAgent"""

        try:
            # Prepare input for critic
            validation_input = {
                "reason_card": context.get_metadata("reason_card", {}),
                "analysis_outputs": workflow_results.get("analysis", {}),
                "source_data": context.get_metadata("retrieved_facts", {})
            }

            # Get available tools (critic typically doesn't use external tools)
            available_tools = self._get_available_tools_for_agent("critic", context)

            # Execute validation
            validation_result = self.critic.process(validation_input, context, available_tools)

            return validation_result

        except Exception as e:
            return {
                "success": False,
                "error": f"Validation stage error: {str(e)}"
            }

    def _handle_revision(self, workflow_results: Dict[str, Any], context: Any) -> Dict[str, Any]:
        """Handle automatic revision based on critic feedback"""

        try:
            validation_results = workflow_results.get("validation", {})
            auto_revisions = validation_results.get("auto_revisions", [])

            if not auto_revisions:
                return {
                    "success": False,
                    "message": "No auto-revisions available, manual review required"
                }

            # Apply auto-revisions to reason card
            reason_card = context.get_metadata("reason_card", {}).copy()
            revisions_applied = 0

            for revision in auto_revisions:
                section = revision.get("section", "")
                revised_content = revision.get("revised", "")

                # Apply revision based on section
                if section == "prediction_summary.confidence_level":
                    if "prediction_summary" in reason_card:
                        reason_card["prediction_summary"]["confidence_level"] = revised_content
                        revisions_applied += 1

                elif section == "recommendations" and "revised" in revision:
                    # Replace specific recommendation
                    if "recommendations" in reason_card:
                        for rec_category in ["immediate_actions", "strategic_implications"]:
                            if rec_category in reason_card["recommendations"]:
                                actions = reason_card["recommendations"][rec_category]
                                for i, action in enumerate(actions):
                                    if action == revision.get("current", ""):
                                        actions[i] = revised_content
                                        revisions_applied += 1
                                        break

            # Store revised reason card
            context.add_metadata("reason_card", reason_card)

            return {
                "success": True,
                "revisions_applied": revisions_applied,
                "revised_reason_card": reason_card,
                "message": f"Applied {revisions_applied} auto-revisions"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Revision handling error: {str(e)}"
            }

    def _execute_feature_engineering(self, dataset_name: str, target_features: List[str], context: Any) -> Dict[str, Any]:
        """Execute feature engineering using FeatureEngineeringTool"""

        try:
            from .feature_engineering import FeatureEngineeringTool
            fe_tool = FeatureEngineeringTool()

            fe_params = {
                "dataset_name": dataset_name,
                "feature_types": target_features if target_features else ["volume", "growth", "consistency", "behavioral"],
                "target_month": 12,
                "time_window": 3
            }

            result = fe_tool.safe_execute(fe_params, context)
            return {"success": "error" not in result, **result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_trajectory_classification(self, features_dataset: str, context: Any) -> Dict[str, Any]:
        """Execute trajectory classification using TrajectoryClassificationTool"""

        try:
            from .feature_engineering import TrajectoryClassificationTool
            tc_tool = TrajectoryClassificationTool()

            tc_params = {
                "features_dataset": features_dataset,
                "trajectory_types": ["steady", "slow_start", "fast_launch", "volatile", "flat"]
            }

            result = tc_tool.safe_execute(tc_params, context)
            return {"success": "error" not in result, **result}

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _execute_prediction_modeling(self, context: Any) -> Dict[str, Any]:
        """Execute prediction modeling using actual feature data"""

        # Get features dataset from context
        datasets = context.get_all_datasets()

        if not datasets:
            return {
                "success": False,
                "error": "No feature datasets available for prediction modeling. Execute feature engineering first."
            }

        # Find features dataset (looking for pharmaceutical or general features)
        features_dataset = None
        for name, df in datasets.items():
            if "feature" in name.lower() or "pharmaceutical" in name.lower():
                features_dataset = df
                break

        if features_dataset is None:
            return {
                "success": False,
                "error": "No feature dataset found. Execute pharmaceutical_feature_engineering or feature_engineering first."
            }

        # Basic validation of features dataset
        required_columns = ["PRESCRIBER_NPI_NBR"]  # At minimum need prescriber identifier

        if not any(col in features_dataset.columns for col in required_columns):
            return {
                "success": False,
                "error": f"Features dataset missing required columns. Has: {list(features_dataset.columns)}"
            }

        # TODO: Implement actual ML modeling here
        # For now, return indication that real data is needed
        return {
            "success": True,
            "message": "Prediction modeling requires actual implementation with sklearn/statsmodels",
            "data_available": True,
            "feature_count": len(features_dataset.columns),
            "sample_size": len(features_dataset),
            "note": "Replace this with actual ML model training and evaluation"
        }

    def _get_available_tools_for_agent(self, agent_type: str, context: Any) -> Dict[str, Any]:
        """Get tools available for specific agent type"""

        # Import actual tools from registry
        from . import get_all_tools
        all_tools = get_all_tools()

        # Return actual tool instances for each agent type
        if agent_type == "planner":
            return {
                "web_search": all_tools.get("web_search"),
                "clinical_context_search": all_tools.get("clinical_context_search")
            }
        elif agent_type == "retriever":
            return {
                "web_search": all_tools.get("web_search"),
                "clinical_context_search": all_tools.get("clinical_context_search"),
                "bigquery_sql_query": all_tools.get("bigquery_sql_query")
            }
        else:
            return {}

    def _get_previous_analysis_context(self, context: Any) -> Dict[str, Any]:
        """Get context from previous analyses"""

        return {
            "previous_queries": [],  # Would track previous queries
            "existing_datasets": list(context.get_all_datasets().keys()),
            "session_history": len(context.conversation_history) if hasattr(context, 'conversation_history') else 0
        }

    def _extract_drug_name(self, query: str) -> str:
        """Extract drug name from query (simple implementation)"""

        # Simple keyword extraction - could be enhanced with NLP
        common_drugs = ["humira", "enbrel", "remicade", "stelara", "cosentyx", "taltz"]
        query_lower = query.lower()

        for drug in common_drugs:
            if drug in query_lower:
                return drug.upper()

        # Try to find capitalized words that might be drug names
        words = query.split()
        for word in words:
            if word.isupper() and len(word) > 3:
                return word

        return ""