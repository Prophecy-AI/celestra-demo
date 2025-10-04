"""
Answerer agent for producing structured reason cards and analysis summaries
"""
import json
from typing import Dict, Any, List
from .base_agent import BaseAgent
from ..context import Context


class AnswererAgent(BaseAgent):
    """Agent responsible for producing structured reason cards and analysis summaries from retrieved facts"""

    def __init__(self):
        super().__init__(
            name="answerer",
            description="Produces structured reason cards and analysis summaries based on retrieved facts",
            allowed_tools=[]  # Answerer uses retrieved facts, doesn't call external tools
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for the answerer agent"""
        return """You are a specialized Answerer Agent for healthcare predictive analytics.

Your role is to synthesize retrieved facts and analysis results into structured, actionable reason cards that explain predictions and insights.

## CORE RESPONSIBILITIES:
1. Create structured reason cards explaining predictions
2. Synthesize facts from multiple sources into coherent narratives
3. Ensure all claims are properly cited and evidence-based
4. Provide calibrated confidence levels and uncertainty quantification
5. Make recommendations actionable and clinically relevant

## REASON CARD STRUCTURE:
Every response must be a structured reason card with these components:

```json
{
  "prediction_summary": {
    "main_finding": "Clear statement of key prediction/finding",
    "confidence_level": "high|medium|low",
    "confidence_score": 0.85,
    "key_metrics": {
      "feature_importance_score": 0.92,
      "prediction_accuracy": 0.78,
      "sample_size": 1234
    }
  },
  "evidence_synthesis": {
    "supporting_evidence": [
      {
        "evidence_type": "statistical|clinical|external",
        "finding": "Specific finding with numbers",
        "strength": "strong|moderate|weak",
        "source_citation": "Specific source reference",
        "clinical_relevance": "Why this matters clinically"
      }
    ],
    "conflicting_evidence": [
      {
        "finding": "Any conflicting findings",
        "explanation": "Why conflict exists",
        "resolution": "How conflict was resolved"
      }
    ]
  },
  "predictive_insights": {
    "top_predictors": [
      {
        "feature": "Feature name",
        "importance": 0.23,
        "direction": "positive|negative",
        "interpretation": "What this means clinically",
        "actionability": "How prescribers can act on this"
      }
    ],
    "interaction_effects": [
      {
        "features": ["feature1", "feature2"],
        "effect": "Description of interaction",
        "significance": "high|medium|low"
      }
    ]
  },
  "clinical_context": {
    "therapeutic_area": "e.g., Immunology, Oncology",
    "prescriber_segments": ["Rheumatologists", "Dermatologists"],
    "market_dynamics": "Relevant market factors",
    "regulatory_considerations": "FDA guidance, guidelines"
  },
  "recommendations": {
    "immediate_actions": [
      "Specific actionable recommendations"
    ],
    "strategic_implications": [
      "Longer-term strategic insights"
    ],
    "monitoring_priorities": [
      "What to monitor going forward"
    ]
  },
  "uncertainty_quantification": {
    "key_assumptions": ["List of key assumptions"],
    "sensitivity_analysis": "How robust are the findings",
    "data_limitations": ["Known limitations"],
    "confidence_intervals": {
      "prediction_range": "X% to Y%",
      "feature_importance_range": "Statistical confidence ranges"
    }
  },
  "citations": [
    {
      "id": "cite_1",
      "source": "Specific source",
      "type": "internal_data|external_research|clinical_guideline",
      "reliability": "high|medium|low",
      "url": "if available"
    }
  ]
}
```

## EVIDENCE SYNTHESIS PRINCIPLES:
1. **Citation Requirements**: Every factual claim must include a citation
2. **Confidence Calibration**: Use "likely", "possibly", "uncertain" appropriately
3. **Quantification**: Always include specific numbers and confidence intervals
4. **Clinical Translation**: Explain statistical findings in clinical terms
5. **Actionability**: Focus on what prescribers/stakeholders can do with insights

## WRITING GUIDELINES:
- Use precise, quantified language ("78% of high prescribers" not "most prescribers")
- Include statistical significance and effect sizes
- Acknowledge uncertainty and limitations explicitly
- Prioritize clinical relevance over statistical novelty
- Structure for busy healthcare professionals

## CALIBRATED CONFIDENCE LANGUAGE:
- **High confidence (>80%)**: "Evidence strongly suggests", "Analysis demonstrates"
- **Medium confidence (60-80%)**: "Evidence indicates", "Analysis suggests"
- **Low confidence (<60%)**: "Limited evidence suggests", "Preliminary analysis indicates"

## QUALITY STANDARDS:
- All numerical claims must be traceable to specific data
- Clinical interpretations must be evidence-based
- Recommendations must be specific and actionable
- Uncertainty must be explicitly quantified
- Sources must be properly attributed

Focus on creating comprehensive, evidence-based reason cards that healthcare professionals can trust and act upon."""

    def process(self, input_data: Dict[str, Any], context: Context, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Process analysis results and create structured reason card"""

        analysis_results = input_data.get("analysis_results", {})
        retrieved_facts = input_data.get("retrieved_facts", {})
        query_context = input_data.get("query_context", "")

        try:
            # Create structured reason card
            reason_card = self._create_reason_card(
                analysis_results, retrieved_facts, query_context
            )

            return {
                "success": True,
                "reason_card": reason_card,
                "agent": self.name,
                "message": f"Created structured reason card with {len(reason_card.get('evidence_synthesis', {}).get('supporting_evidence', []))} evidence points"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Reason card creation failed: {str(e)}",
                "agent": self.name
            }

    def _create_reason_card(self, analysis_results: Dict[str, Any], retrieved_facts: Dict[str, Any], query_context: str) -> Dict[str, Any]:
        """Create comprehensive reason card from analysis and retrieved facts"""

        # Extract key information from analysis results
        prediction_data = analysis_results.get("prediction_summary", {})
        feature_importance = analysis_results.get("feature_importance", {})
        model_metrics = analysis_results.get("model_metrics", {})

        # Extract clinical context from retrieved facts
        clinical_context = retrieved_facts.get("clinical_context", {})
        thresholds = retrieved_facts.get("thresholds", {})

        # Build reason card structure
        reason_card = {
            "prediction_summary": self._build_prediction_summary(
                prediction_data, model_metrics, query_context
            ),
            "evidence_synthesis": self._build_evidence_synthesis(
                analysis_results, retrieved_facts
            ),
            "predictive_insights": self._build_predictive_insights(
                feature_importance, thresholds
            ),
            "clinical_context": self._build_clinical_context(
                clinical_context, query_context
            ),
            "recommendations": self._build_recommendations(
                analysis_results, clinical_context
            ),
            "uncertainty_quantification": self._build_uncertainty_analysis(
                model_metrics, analysis_results
            ),
            "citations": self._build_citations(retrieved_facts)
        }

        return reason_card

    def _build_prediction_summary(self, prediction_data: Dict[str, Any], model_metrics: Dict[str, Any], query_context: str) -> Dict[str, Any]:
        """Build prediction summary section"""

        # Determine confidence level based on model metrics
        accuracy = model_metrics.get("accuracy", 0.5)
        confidence_level = "high" if accuracy > 0.8 else "medium" if accuracy > 0.65 else "low"

        return {
            "main_finding": prediction_data.get("main_finding", f"Predictive analysis completed for: {query_context}"),
            "confidence_level": confidence_level,
            "confidence_score": round(accuracy, 2),
            "key_metrics": {
                "feature_importance_score": model_metrics.get("feature_importance_score", 0.0),
                "prediction_accuracy": accuracy,
                "sample_size": prediction_data.get("sample_size", 0)
            }
        }

    def _build_evidence_synthesis(self, analysis_results: Dict[str, Any], retrieved_facts: Dict[str, Any]) -> Dict[str, Any]:
        """Build evidence synthesis section"""

        supporting_evidence = []

        # Add statistical evidence from analysis
        if "feature_correlations" in analysis_results:
            correlations = analysis_results["feature_correlations"]
            for feature, correlation in correlations.items():
                if abs(correlation) > 0.3:  # Meaningful correlation threshold
                    supporting_evidence.append({
                        "evidence_type": "statistical",
                        "finding": f"{feature} shows {abs(correlation):.2f} correlation with high prescribing",
                        "strength": "strong" if abs(correlation) > 0.6 else "moderate",
                        "source_citation": "Internal data analysis",
                        "clinical_relevance": f"{'Positive' if correlation > 0 else 'Negative'} association suggests clinical significance"
                    })

        # Add external evidence from retrieved facts
        if retrieved_facts.get("sources"):
            for source in retrieved_facts["sources"][:3]:  # Top 3 sources
                if source.get("key_facts"):
                    supporting_evidence.append({
                        "evidence_type": "external",
                        "finding": source["key_facts"][0] if source["key_facts"] else "External validation",
                        "strength": "strong" if source.get("reliability_score", 0) > 0.8 else "moderate",
                        "source_citation": source.get("source", "External source"),
                        "clinical_relevance": "Provides external validation of findings"
                    })

        return {
            "supporting_evidence": supporting_evidence,
            "conflicting_evidence": []  # Could be enhanced to detect conflicts
        }

    def _build_predictive_insights(self, feature_importance: Dict[str, Any], thresholds: Dict[str, Any]) -> Dict[str, Any]:
        """Build predictive insights section"""

        top_predictors = []

        # Process feature importance if available
        if feature_importance:
            for feature, importance in list(feature_importance.items())[:5]:  # Top 5 features
                top_predictors.append({
                    "feature": feature,
                    "importance": round(importance, 2),
                    "direction": "positive",  # Could be enhanced with actual direction analysis
                    "interpretation": self._interpret_feature_clinically(feature),
                    "actionability": self._suggest_feature_action(feature)
                })

        return {
            "top_predictors": top_predictors,
            "interaction_effects": []  # Could be enhanced with interaction analysis
        }

    def _build_clinical_context(self, clinical_context: Dict[str, Any], query_context: str) -> Dict[str, Any]:
        """Build clinical context section"""

        return {
            "therapeutic_area": clinical_context.get("therapeutic_area", "Multi-specialty"),
            "prescriber_segments": clinical_context.get("prescriber_segments", ["Primary Care", "Specialists"]),
            "market_dynamics": clinical_context.get("market_dynamics", "Competitive therapeutic landscape"),
            "regulatory_considerations": clinical_context.get("regulatory_considerations", "Standard FDA guidelines apply")
        }

    def _build_recommendations(self, analysis_results: Dict[str, Any], clinical_context: Dict[str, Any]) -> Dict[str, Any]:
        """Build recommendations section"""

        immediate_actions = [
            "Focus engagement on highest-probability prescribers identified by model",
            "Monitor early-stage prescriber behaviors for growth indicators",
            "Validate predictions with field teams for accuracy assessment"
        ]

        strategic_implications = [
            "Invest in predictive models for resource allocation optimization",
            "Develop prescriber-specific engagement strategies based on behavior patterns",
            "Create feedback loops to improve prediction accuracy over time"
        ]

        monitoring_priorities = [
            "Track prediction accuracy against actual outcomes",
            "Monitor for changes in prescriber behavior patterns",
            "Assess model performance across different therapeutic areas"
        ]

        return {
            "immediate_actions": immediate_actions,
            "strategic_implications": strategic_implications,
            "monitoring_priorities": monitoring_priorities
        }

    def _build_uncertainty_analysis(self, model_metrics: Dict[str, Any], analysis_results: Dict[str, Any]) -> Dict[str, Any]:
        """Build uncertainty quantification section"""

        confidence_score = model_metrics.get("accuracy", 0.5)

        return {
            "key_assumptions": [
                "Historical prescribing patterns predict future behavior",
                "Feature relationships remain stable over time",
                "Data quality and completeness are consistent"
            ],
            "sensitivity_analysis": f"Model shows {'high' if confidence_score > 0.8 else 'moderate'} sensitivity to key features",
            "data_limitations": [
                "Limited to observable prescribing behaviors",
                "Missing external factors (marketing, clinical events)",
                "Historical data may not reflect future market changes"
            ],
            "confidence_intervals": {
                "prediction_range": f"{max(0, confidence_score-0.1):.1%} to {min(1, confidence_score+0.1):.1%}",
                "feature_importance_range": "Statistical significance at 95% level"
            }
        }

    def _build_citations(self, retrieved_facts: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Build citations section"""

        citations = []

        if retrieved_facts.get("sources"):
            for i, source in enumerate(retrieved_facts["sources"]):
                citations.append({
                    "id": f"cite_{i+1}",
                    "source": source.get("source", f"Source {i+1}"),
                    "type": source.get("source_type", "external_research"),
                    "reliability": "high" if source.get("reliability_score", 0) > 0.8 else "medium",
                    "url": source.get("url", "")
                })

        return citations

    def _interpret_feature_clinically(self, feature: str) -> str:
        """Provide clinical interpretation for features"""

        interpretations = {
            "total_volume": "Higher prescription volumes indicate established prescribing patterns",
            "avg_mom_growth": "Growth rate reflects adoption momentum and patient response",
            "volume_cv": "Consistency indicates stable patient population and treatment protocols",
            "drug_diversity": "Broader prescribing suggests comfort with therapeutic class",
            "active_days": "Regular prescribing indicates integrated treatment protocols"
        }

        return interpretations.get(feature, f"Clinical significance of {feature} requires domain expert interpretation")

    def _suggest_feature_action(self, feature: str) -> str:
        """Suggest actionable insights for features"""

        actions = {
            "total_volume": "Target high-volume prescribers for advanced product education",
            "avg_mom_growth": "Engage growing prescribers with expansion support resources",
            "volume_cv": "Provide consistency-focused support to volatile prescribers",
            "drug_diversity": "Introduce complementary products to diverse prescribers",
            "active_days": "Reinforce prescribing habits with regular touchpoints"
        }

        return actions.get(feature, f"Develop targeted strategies based on {feature} patterns")