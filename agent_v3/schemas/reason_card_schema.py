"""
Structured schema for reason cards in predictive analytics
"""
from typing import List, Dict, Any, Optional, Union, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime


class KeyMetrics(BaseModel):
    """Key metrics for prediction summary"""
    feature_importance_score: float = Field(ge=0.0, le=1.0, description="Overall feature importance score")
    prediction_accuracy: float = Field(ge=0.0, le=1.0, description="Model prediction accuracy")
    sample_size: int = Field(ge=0, description="Sample size used for analysis")
    confidence_interval_lower: Optional[float] = Field(None, description="Lower bound of confidence interval")
    confidence_interval_upper: Optional[float] = Field(None, description="Upper bound of confidence interval")


class PredictionSummary(BaseModel):
    """Prediction summary section of reason card"""
    main_finding: str = Field(min_length=10, description="Clear statement of key prediction/finding")
    confidence_level: Literal["high", "medium", "low"] = Field(description="Overall confidence level")
    confidence_score: float = Field(ge=0.0, le=1.0, description="Numerical confidence score")
    key_metrics: KeyMetrics = Field(description="Key metrics supporting the prediction")

    @validator("confidence_score")
    def validate_confidence_alignment(cls, v, values):
        """Ensure confidence score aligns with confidence level"""
        if "confidence_level" in values:
            level = values["confidence_level"]
            if level == "high" and v < 0.75:
                raise ValueError("High confidence level requires score >= 0.75")
            elif level == "medium" and (v < 0.5 or v > 0.85):
                raise ValueError("Medium confidence level requires score between 0.5 and 0.85")
            elif level == "low" and v > 0.65:
                raise ValueError("Low confidence level requires score <= 0.65")
        return v


class Evidence(BaseModel):
    """Individual evidence item"""
    evidence_type: Literal["statistical", "clinical", "external"] = Field(description="Type of evidence")
    finding: str = Field(min_length=10, description="Specific finding with numbers")
    strength: Literal["strong", "moderate", "weak"] = Field(description="Strength of evidence")
    source_citation: str = Field(min_length=5, description="Specific source reference")
    clinical_relevance: str = Field(min_length=10, description="Why this matters clinically")


class ConflictingEvidence(BaseModel):
    """Conflicting evidence item"""
    finding: str = Field(min_length=10, description="Conflicting finding")
    explanation: str = Field(min_length=10, description="Why conflict exists")
    resolution: str = Field(min_length=10, description="How conflict was resolved")


class EvidenceSynthesis(BaseModel):
    """Evidence synthesis section"""
    supporting_evidence: List[Evidence] = Field(min_items=1, description="Supporting evidence items")
    conflicting_evidence: List[ConflictingEvidence] = Field(default=[], description="Conflicting evidence items")

    @validator("supporting_evidence")
    def validate_evidence_quality(cls, v):
        """Ensure at least one strong evidence"""
        strong_evidence_count = sum(1 for evidence in v if evidence.strength == "strong")
        if strong_evidence_count == 0 and len(v) < 3:
            raise ValueError("Must have at least one strong evidence or 3+ moderate/weak evidence items")
        return v


class Predictor(BaseModel):
    """Individual predictor feature"""
    feature: str = Field(min_length=3, description="Feature name")
    importance: float = Field(ge=0.0, le=1.0, description="Feature importance score")
    direction: Literal["positive", "negative"] = Field(description="Direction of association")
    interpretation: str = Field(min_length=10, description="Clinical interpretation")
    actionability: str = Field(min_length=10, description="How prescribers can act on this")


class InteractionEffect(BaseModel):
    """Feature interaction effect"""
    features: List[str] = Field(min_items=2, max_items=3, description="Interacting features")
    effect: str = Field(min_length=10, description="Description of interaction")
    significance: Literal["high", "medium", "low"] = Field(description="Significance level")


class PredictiveInsights(BaseModel):
    """Predictive insights section"""
    top_predictors: List[Predictor] = Field(min_items=1, max_items=10, description="Top predictive features")
    interaction_effects: List[InteractionEffect] = Field(default=[], description="Feature interactions")

    @validator("top_predictors")
    def validate_importance_order(cls, v):
        """Ensure predictors are ordered by importance"""
        importances = [p.importance for p in v]
        if importances != sorted(importances, reverse=True):
            raise ValueError("Predictors must be ordered by importance (descending)")
        return v


class ClinicalContext(BaseModel):
    """Clinical context section"""
    therapeutic_area: str = Field(min_length=3, description="Therapeutic area")
    prescriber_segments: List[str] = Field(min_items=1, description="Target prescriber segments")
    market_dynamics: str = Field(min_length=10, description="Relevant market factors")
    regulatory_considerations: str = Field(min_length=10, description="FDA guidance, guidelines")


class Recommendations(BaseModel):
    """Recommendations section"""
    immediate_actions: List[str] = Field(min_items=1, description="Immediate actionable recommendations")
    strategic_implications: List[str] = Field(min_items=1, description="Strategic insights")
    monitoring_priorities: List[str] = Field(min_items=1, description="What to monitor")

    @validator("immediate_actions", "strategic_implications", "monitoring_priorities")
    def validate_actionability(cls, v):
        """Ensure recommendations are specific and actionable"""
        for item in v:
            if len(item.split()) < 4:
                raise ValueError("Recommendations must be specific (at least 4 words)")
            if any(vague_word in item.lower() for vague_word in ["consider", "explore", "think about"]):
                raise ValueError("Recommendations should be actionable, avoid vague language")
        return v


class ConfidenceInterval(BaseModel):
    """Confidence interval specification"""
    prediction_range: str = Field(pattern=r"^\d+\.?\d*% to \d+\.?\d*%$", description="Prediction confidence range")
    feature_importance_range: str = Field(min_length=10, description="Feature importance confidence range")


class UncertaintyQuantification(BaseModel):
    """Uncertainty quantification section"""
    key_assumptions: List[str] = Field(min_items=1, description="Key assumptions made")
    sensitivity_analysis: str = Field(min_length=10, description="Robustness assessment")
    data_limitations: List[str] = Field(min_items=1, description="Known data limitations")
    confidence_intervals: ConfidenceInterval = Field(description="Statistical confidence ranges")


class Citation(BaseModel):
    """Individual citation"""
    id: str = Field(min_length=3, description="Citation identifier")
    source: str = Field(min_length=5, description="Source name")
    type: Literal["internal_data", "external_research", "clinical_guideline"] = Field(description="Source type")
    reliability: Literal["high", "medium", "low"] = Field(description="Source reliability")
    url: Optional[str] = Field(None, description="URL if available")


class ReasonCardSchema(BaseModel):
    """Complete reason card schema for predictive analytics"""

    # Metadata
    generated_at: datetime = Field(default_factory=datetime.now, description="Generation timestamp")
    query_context: str = Field(min_length=10, description="Original query context")
    agent_version: str = Field(default="v3.0", description="Agent version")

    # Core sections
    prediction_summary: PredictionSummary = Field(description="Main prediction findings")
    evidence_synthesis: EvidenceSynthesis = Field(description="Supporting and conflicting evidence")
    predictive_insights: PredictiveInsights = Field(description="Key predictors and interactions")
    clinical_context: ClinicalContext = Field(description="Clinical and market context")
    recommendations: Recommendations = Field(description="Actionable recommendations")
    uncertainty_quantification: UncertaintyQuantification = Field(description="Uncertainty analysis")
    citations: List[Citation] = Field(min_items=1, description="Source citations")

    class Config:
        """Pydantic configuration"""
        validate_assignment = True
        extra = "forbid"  # Don't allow extra fields
        schema_extra = {
            "example": {
                "generated_at": "2024-01-15T10:30:00Z",
                "query_context": "Predict high prescribers in Month 12 using Month 1-3 data",
                "prediction_summary": {
                    "main_finding": "Early volume patterns predict 78% of high prescribers at Month 12",
                    "confidence_level": "high",
                    "confidence_score": 0.82,
                    "key_metrics": {
                        "feature_importance_score": 0.89,
                        "prediction_accuracy": 0.78,
                        "sample_size": 1247
                    }
                },
                "evidence_synthesis": {
                    "supporting_evidence": [
                        {
                            "evidence_type": "statistical",
                            "finding": "Total volume shows 0.65 correlation with Month 12 outcomes",
                            "strength": "strong",
                            "source_citation": "Internal prescription data analysis",
                            "clinical_relevance": "Strong early prescribing predicts sustained usage"
                        }
                    ]
                },
                "citations": [
                    {
                        "id": "cite_1",
                        "source": "Internal prescription database",
                        "type": "internal_data",
                        "reliability": "high"
                    }
                ]
            }
        }

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON schema for LLM structured output"""
        return self.schema()

    def validate_clinical_safety(self) -> List[str]:
        """Additional validation for clinical safety"""
        safety_issues = []

        # Check for safety-related terms in recommendations
        all_recommendations = (
            self.recommendations.immediate_actions +
            self.recommendations.strategic_implications
        )

        for rec in all_recommendations:
            if any(term in rec.lower() for term in ["ignore", "bypass", "contraindication"]):
                safety_issues.append(f"Potential safety concern in recommendation: {rec}")

        # Check confidence calibration
        if self.prediction_summary.confidence_level == "high" and self.prediction_summary.confidence_score < 0.8:
            safety_issues.append("High confidence claim not supported by score")

        return safety_issues