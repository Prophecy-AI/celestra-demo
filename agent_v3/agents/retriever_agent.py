"""
Retriever agent for gathering specifications, thresholds, and external context
"""
import json
from typing import Dict, Any, List
from .base_agent import BaseAgent
from ..context import Context


class RetrieverAgent(BaseAgent):
    """Agent responsible for retrieving specifications, thresholds, concepts, and external context"""

    def __init__(self):
        super().__init__(
            name="retriever",
            description="Retrieves feature specifications, thresholds, concepts, and external validation context",
            allowed_tools=["web_search", "clinical_context_search", "bigquery_sql_query"]
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for the retriever agent"""
        return """You are a specialized Retriever Agent for healthcare predictive analytics.

Your role is to gather all necessary specifications, thresholds, concepts, and external validation context needed for accurate analysis.

## CORE RESPONSIBILITIES:
1. Retrieve feature definitions and calculation specifications
2. Gather clinical thresholds and benchmarks
3. Pull external validation context from medical literature
4. Collect regulatory and clinical guidelines
5. Provide structured knowledge base for analysis

## RETRIEVAL CATEGORIES:

### 1. FEATURE SPECIFICATIONS
- Volume metrics: Total prescriptions, quantities, patient counts
- Growth metrics: MoM growth rates, CAGR, acceleration patterns
- Consistency metrics: CV, volatility, run-lengths
- Behavioral metrics: Drug diversity, temporal patterns

### 2. CLINICAL THRESHOLDS
- High prescriber definitions (e.g., >95th percentile, >500 scripts/month)
- Growth rate benchmarks (e.g., >20% MoM = fast growth)
- Volatility thresholds (e.g., CV >0.5 = high volatility)
- Market penetration levels

### 3. EXTERNAL CONTEXT
- Drug indication and market context
- Prescribing guidelines and best practices
- Market dynamics and competitive landscape
- Regulatory considerations

### 4. CONCEPT DEFINITIONS
- Trajectory patterns: steady, fast-launch, volatile, slow-start
- Predictive concepts: momentum, consistency, breadth
- Risk factors and contraindications

## OUTPUT FORMAT:
Always return structured retrieval results:

```json
{
  "retrieval_type": "specifications|thresholds|clinical_context|concepts",
  "query_context": "description of what was requested",
  "sources": [
    {
      "source_type": "internal|external|clinical_literature|regulatory",
      "source": "specific source identifier",
      "reliability_score": 0.9,
      "content": "retrieved content",
      "key_facts": ["list of key facts"],
      "thresholds": {"threshold_name": "threshold_value"}
    }
  ],
  "consolidated_facts": ["combined facts from all sources"],
  "recommendations": ["recommendations for analysis based on retrieved context"],
  "confidence_level": "high|medium|low"
}
```

## SEARCH STRATEGIES:

### For Drug Context:
- Search for FDA indications and approvals
- Look up prescribing guidelines from medical societies
- Find market analysis and competitive intelligence
- Retrieve clinical trial data and efficacy results

### For Threshold Setting:
- Search for industry benchmarks and percentiles
- Look up clinical significance thresholds
- Find regulatory guidance on meaningful changes
- Retrieve peer-reviewed threshold recommendations

### For Pattern Recognition:
- Search for prescribing behavior studies
- Look up adoption curve research
- Find physician behavior change literature
- Retrieve market penetration models

## QUALITY ASSURANCE:
- Prioritize authoritative sources (FDA, medical societies, peer-reviewed)
- Cross-validate information across multiple sources
- Flag conflicting information for review
- Assess currency and relevance of retrieved information

## INTEGRATION FOCUS:
Your retrievals should directly support:
- Feature engineering parameter selection
- Threshold setting for classifications
- Model interpretation and validation
- Clinical relevance assessment of findings

Always provide citations and assess the reliability of retrieved information."""

    def process(self, input_data: Dict[str, Any], context: Context, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Process retrieval request and gather relevant context"""

        retrieval_request = input_data.get("request", "")
        retrieval_type = input_data.get("type", "general")
        drug_name = input_data.get("drug_name", "")
        specific_needs = input_data.get("specific_needs", [])

        try:
            # Determine retrieval strategy based on type
            if retrieval_type == "clinical_context" and drug_name:
                return self._retrieve_clinical_context(drug_name, available_tools, context)
            elif retrieval_type == "thresholds":
                return self._retrieve_thresholds(retrieval_request, available_tools, context)
            elif retrieval_type == "specifications":
                return self._retrieve_feature_specifications(retrieval_request, available_tools, context)
            else:
                return self._general_retrieval(retrieval_request, available_tools, context)

        except Exception as e:
            return {
                "success": False,
                "error": f"Retrieval failed: {str(e)}",
                "agent": self.name
            }

    def _retrieve_clinical_context(self, drug_name: str, available_tools: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """Retrieve clinical context for a specific drug"""

        # Use clinical context search tool
        if "clinical_context_search" in available_tools:
            tool = available_tools["clinical_context_search"]

            # Search for different types of clinical information
            searches = [
                {"drug_name": drug_name, "search_type": "indication"},
                {"drug_name": drug_name, "search_type": "prescribing_pattern"},
                {"drug_name": drug_name, "search_type": "clinical_trial"}
            ]

            consolidated_results = {
                "retrieval_type": "clinical_context",
                "query_context": f"Clinical context for {drug_name}",
                "sources": [],
                "consolidated_facts": [],
                "recommendations": [],
                "confidence_level": "medium"
            }

            for search_params in searches:
                try:
                    result = tool.safe_execute(search_params, context)
                    if result.get("clinical_context"):
                        clinical_data = result["clinical_context"]

                        source_entry = {
                            "source_type": "clinical_literature",
                            "source": f"Tavily clinical search - {search_params['search_type']}",
                            "reliability_score": 0.8,
                            "content": clinical_data.get("clinical_summary", ""),
                            "key_facts": [source["title"] for source in clinical_data.get("sources", [])[:3]],
                            "thresholds": {}
                        }

                        consolidated_results["sources"].append(source_entry)
                        consolidated_results["consolidated_facts"].extend([
                            f"{drug_name} indications: {clinical_data.get('clinical_summary', '')[:200]}..."
                        ])

                except Exception as e:
                    continue  # Skip failed searches

            # Add recommendations based on retrieved context
            if consolidated_results["sources"]:
                consolidated_results["recommendations"] = [
                    f"Consider {drug_name}-specific prescribing patterns in analysis",
                    "Validate findings against known clinical indications",
                    "Account for indication-specific prescriber behaviors"
                ]
                consolidated_results["confidence_level"] = "high"

            return {
                "success": True,
                "retrieval_results": consolidated_results,
                "agent": self.name,
                "message": f"Retrieved clinical context for {drug_name} from {len(consolidated_results['sources'])} sources"
            }

        return {
            "success": False,
            "error": "Clinical context search tool not available",
            "agent": self.name
        }

    def _retrieve_thresholds(self, request: str, available_tools: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """Retrieve industry thresholds and benchmarks"""

        # Define standard healthcare analytics thresholds
        standard_thresholds = {
            "high_prescriber_volume": {
                "monthly_scripts": 100,
                "percentile_threshold": 95,
                "annual_volume": 1200,
                "description": "Thresholds for defining high-volume prescribers"
            },
            "growth_patterns": {
                "fast_growth": 20,  # >20% MoM
                "moderate_growth": 5,  # 5-20% MoM
                "slow_growth": 0,    # 0-5% MoM
                "decline": 0,        # <0% MoM
                "description": "Month-over-month growth rate categories"
            },
            "volatility_measures": {
                "low_volatility": 0.2,   # CV < 0.2
                "medium_volatility": 0.5, # CV 0.2-0.5
                "high_volatility": 0.5,   # CV > 0.5
                "description": "Coefficient of variation thresholds for consistency"
            },
            "trajectory_classification": {
                "steady_cv_threshold": 0.3,
                "fast_launch_growth": 25,
                "volatile_cv_threshold": 0.6,
                "description": "Thresholds for trajectory pattern classification"
            }
        }

        # Use web search for additional validation if available
        external_validation = []
        if "web_search" in available_tools:
            tool = available_tools["web_search"]

            search_queries = [
                "healthcare prescriber volume benchmarks thresholds",
                "physician prescribing behavior analysis metrics",
                "pharmaceutical market research thresholds"
            ]

            for query in search_queries:
                try:
                    result = tool.safe_execute({"query": query, "max_results": 3}, context)
                    if result.get("search_results"):
                        external_validation.extend(result["search_results"]["results"][:2])
                except:
                    continue

        # Compile comprehensive threshold results
        retrieval_results = {
            "retrieval_type": "thresholds",
            "query_context": request,
            "sources": [
                {
                    "source_type": "internal",
                    "source": "Healthcare Analytics Standards",
                    "reliability_score": 0.9,
                    "content": "Standard healthcare analytics thresholds",
                    "key_facts": list(standard_thresholds.keys()),
                    "thresholds": standard_thresholds
                }
            ],
            "consolidated_facts": [
                "High prescriber defined as >95th percentile or >100 scripts/month",
                "Fast growth defined as >20% month-over-month increase",
                "High volatility defined as CV > 0.5",
                "Trajectory patterns use combined growth and consistency metrics"
            ],
            "recommendations": [
                "Use percentile-based thresholds for relative ranking",
                "Consider drug-specific volume thresholds",
                "Validate thresholds against clinical significance",
                "Monitor threshold sensitivity in model performance"
            ],
            "confidence_level": "high"
        }

        # Add external validation if found
        if external_validation:
            for i, validation in enumerate(external_validation):
                retrieval_results["sources"].append({
                    "source_type": "external",
                    "source": validation.get("title", f"External Source {i+1}"),
                    "reliability_score": 0.7,
                    "content": validation.get("content", "")[:300],
                    "key_facts": [validation.get("title", "")],
                    "thresholds": {}
                })

        return {
            "success": True,
            "retrieval_results": retrieval_results,
            "agent": self.name,
            "message": f"Retrieved threshold specifications from {len(retrieval_results['sources'])} sources"
        }

    def _retrieve_feature_specifications(self, request: str, available_tools: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """Retrieve detailed feature engineering specifications"""

        feature_specifications = {
            "volume_features": {
                "total_volume": "Sum of DISPENSED_QUANTITY_VAL over time period",
                "avg_volume_per_script": "Mean DISPENSED_QUANTITY_VAL per prescription",
                "total_scripts": "Count of distinct prescriptions",
                "volume_percentile": "Relative ranking among all prescribers"
            },
            "growth_features": {
                "mom_growth": "(Current - Previous) / Previous * 100",
                "cagr": "Compound Annual Growth Rate approximation",
                "growth_volatility": "Standard deviation of month-over-month growth",
                "acceleration": "Second derivative of volume trajectory"
            },
            "consistency_features": {
                "volume_cv": "Standard deviation / Mean volume",
                "run_lengths": "Consecutive periods with prescribing activity",
                "active_ratio": "Active days / Total days in period",
                "consistency_score": "Inverse of coefficient of variation"
            },
            "behavioral_features": {
                "drug_diversity": "Count of unique drugs prescribed",
                "temporal_patterns": "Day-of-week and seasonal patterns",
                "patient_load": "Estimated unique patients served",
                "prescribing_concentration": "Drug diversity / Total prescriptions"
            }
        }

        retrieval_results = {
            "retrieval_type": "specifications",
            "query_context": request,
            "sources": [
                {
                    "source_type": "internal",
                    "source": "Healthcare Analytics Feature Library",
                    "reliability_score": 0.95,
                    "content": "Standard feature engineering specifications for predictive modeling",
                    "key_facts": list(feature_specifications.keys()),
                    "thresholds": {},
                    "specifications": feature_specifications
                }
            ],
            "consolidated_facts": [
                "Volume features capture absolute prescribing levels",
                "Growth features identify trajectory patterns and momentum",
                "Consistency features measure prescribing regularity",
                "Behavioral features capture prescribing style and preferences"
            ],
            "recommendations": [
                "Combine multiple feature types for robust prediction",
                "Normalize features across different scales",
                "Consider interaction effects between feature categories",
                "Validate feature importance with domain experts"
            ],
            "confidence_level": "high"
        }

        return {
            "success": True,
            "retrieval_results": retrieval_results,
            "agent": self.name,
            "message": f"Retrieved feature specifications for {len(feature_specifications)} categories"
        }

    def _general_retrieval(self, request: str, available_tools: Dict[str, Any], context: Context) -> Dict[str, Any]:
        """Handle general retrieval requests"""

        if "web_search" in available_tools:
            tool = available_tools["web_search"]
            try:
                result = tool.safe_execute({
                    "query": request,
                    "max_results": 5,
                    "include_answer": True
                }, context)

                if result.get("search_results"):
                    search_data = result["search_results"]

                    retrieval_results = {
                        "retrieval_type": "general",
                        "query_context": request,
                        "sources": [],
                        "consolidated_facts": [search_data.get("answer", "No consolidated answer available")],
                        "recommendations": ["Review sources for additional context"],
                        "confidence_level": "medium"
                    }

                    # Process search results
                    for result_item in search_data.get("results", []):
                        retrieval_results["sources"].append({
                            "source_type": "external",
                            "source": result_item.get("title", "Unknown"),
                            "reliability_score": result_item.get("score", 0.5),
                            "content": result_item.get("content", "")[:500],
                            "key_facts": [result_item.get("title", "")],
                            "thresholds": {}
                        })

                    return {
                        "success": True,
                        "retrieval_results": retrieval_results,
                        "agent": self.name,
                        "message": f"Retrieved general information from {len(retrieval_results['sources'])} sources"
                    }

            except Exception as e:
                pass  # Fall through to default response

        return {
            "success": False,
            "error": "No suitable retrieval tools available",
            "agent": self.name
        }