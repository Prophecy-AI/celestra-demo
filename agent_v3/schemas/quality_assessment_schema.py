"""
Structured schema for quality assessment results from CriticAgent
"""
from typing import List, Dict, Any, Optional, Literal
from pydantic import BaseModel, Field, validator
from datetime import datetime


class QualityIssue(BaseModel):
    """Individual quality issue"""
    severity: Literal["high", "medium", "low"] = Field(description="Issue severity level")
    issue: str = Field(min_length=10, description="Description of the issue")
    location: str = Field(min_length=5, description="Where the issue was found")
    recommendation: str = Field(min_length=10, description="How to fix the issue")
    category: Literal["faithfulness", "calibration", "actionability", "clinical", "safety"] = Field(
        default="faithfulness", description="Issue category"
    )


class FaithfulnessCheck(BaseModel):
    """Faithfulness assessment results"""
    score: float = Field(ge=0.0, le=1.0, description="Faithfulness score (0-1)")
    passed: bool = Field(description="Whether faithfulness check passed")
    issues: List[QualityIssue] = Field(default=[], description="Identified faithfulness issues")
    citations_validated: int = Field(ge=0, description="Number of citations validated")
    unsupported_claims: int = Field(ge=0, description="Number of unsupported claims found")

    @validator("passed")
    def validate_pass_criteria(cls, v, values):
        """Ensure pass/fail aligns with score and issues"""
        if "score" in values and "issues" in values:
            score = values["score"]
            high_severity_issues = len([i for i in values["issues"] if i.severity == "high"])

            # Should fail if score < 0.8 or has high severity issues
            expected_pass = score >= 0.8 and high_severity_issues == 0
            if v != expected_pass:
                raise ValueError(f"Pass status ({v}) inconsistent with score ({score}) and issues")

        return v


class CalibrationIssue(BaseModel):
    """Calibration-specific issue"""
    issue: str = Field(min_length=10, description="Calibration issue description")
    recommended_language: str = Field(min_length=5, description="Recommended correction")


class CalibrationCheck(BaseModel):
    """Calibration assessment results"""
    score: float = Field(ge=0.0, le=1.0, description="Calibration score (0-1)")
    passed: bool = Field(description="Whether calibration check passed")
    confidence_alignment: Literal["well_calibrated", "overconfident", "underconfident"] = Field(
        description="Assessment of confidence calibration"
    )
    issues: List[CalibrationIssue] = Field(default=[], description="Calibration issues identified")


class ActionabilityIssue(BaseModel):
    """Actionability-specific issue"""
    recommendation: str = Field(min_length=10, description="Original vague recommendation")
    issue: str = Field(min_length=10, description="Why it's not actionable")
    suggested_revision: str = Field(min_length=10, description="More actionable version")


class ActionabilityCheck(BaseModel):
    """Actionability assessment results"""
    score: float = Field(ge=0.0, le=1.0, description="Actionability score (0-1)")
    passed: bool = Field(description="Whether actionability check passed")
    actionable_recommendations: int = Field(ge=0, description="Number of actionable recommendations")
    vague_recommendations: int = Field(ge=0, description="Number of vague recommendations")
    issues: List[ActionabilityIssue] = Field(default=[], description="Actionability issues")


class ClinicalValidation(BaseModel):
    """Clinical validity assessment"""
    score: float = Field(ge=0.0, le=1.0, description="Clinical validity score (0-1)")
    passed: bool = Field(description="Whether clinical validation passed")
    clinical_appropriateness: Literal["high", "medium", "low"] = Field(
        description="Level of clinical appropriateness"
    )
    safety_concerns: List[str] = Field(default=[], description="Identified safety concerns")
    regulatory_compliance: Literal["compliant", "needs_review", "non_compliant"] = Field(
        description="Regulatory compliance status"
    )

    @validator("passed")
    def validate_clinical_pass(cls, v, values):
        """Ensure pass criteria for clinical validation"""
        if "safety_concerns" in values and "score" in values:
            has_safety_issues = len(values["safety_concerns"]) > 0
            score = values["score"]

            # Should fail if there are safety concerns or score < 0.75
            expected_pass = not has_safety_issues and score >= 0.75
            if v != expected_pass:
                raise ValueError("Clinical validation pass status inconsistent with safety concerns or score")

        return v


class ImprovementSuggestion(BaseModel):
    """Improvement suggestion"""
    priority: Literal["high", "medium", "low"] = Field(description="Priority level")
    area: Literal["faithfulness", "calibration", "actionability", "clinical"] = Field(
        description="Area for improvement"
    )
    suggestion: str = Field(min_length=15, description="Specific improvement recommendation")
    expected_impact: str = Field(min_length=10, description="Expected impact of improvement")
    implementation_effort: Literal["low", "medium", "high"] = Field(
        default="medium", description="Estimated effort to implement"
    )


class AutoRevision(BaseModel):
    """Automatic revision suggestion"""
    section: str = Field(min_length=5, description="Section to revise")
    current: str = Field(description="Current content")
    revised: str = Field(min_length=5, description="Revised content")
    reason: str = Field(min_length=10, description="Reason for revision")
    confidence: float = Field(ge=0.0, le=1.0, description="Confidence in auto-revision")


class QualityAssessmentSchema(BaseModel):
    """Complete quality assessment schema"""

    # Metadata
    assessed_at: datetime = Field(default_factory=datetime.now, description="Assessment timestamp")
    critic_version: str = Field(default="v3.0", description="Critic agent version")
    assessment_type: Literal["comprehensive", "standard", "basic"] = Field(
        default="standard", description="Type of assessment performed"
    )

    # Overall assessment
    overall_quality_score: float = Field(ge=0.0, le=1.0, description="Overall quality score")
    assessment_summary: str = Field(min_length=20, description="Brief assessment summary")

    # Detailed checks
    faithfulness_check: FaithfulnessCheck = Field(description="Faithfulness assessment results")
    calibration_check: CalibrationCheck = Field(description="Calibration assessment results")
    actionability_check: ActionabilityCheck = Field(description="Actionability assessment results")
    clinical_validation: ClinicalValidation = Field(description="Clinical validity assessment")

    # Improvement guidance
    improvement_suggestions: List[ImprovementSuggestion] = Field(
        default=[], description="Prioritized improvement suggestions"
    )
    auto_revisions: List[AutoRevision] = Field(
        default=[], description="Automatic revision suggestions"
    )

    # Final determination
    revision_required: bool = Field(description="Whether revision is required")
    approval_status: Literal["approved", "conditional", "rejected"] = Field(
        description="Final approval status"
    )

    class Config:
        """Pydantic configuration"""
        validate_assignment = True
        extra = "forbid"
        schema_extra = {
            "example": {
                "overall_quality_score": 0.82,
                "assessment_summary": "Good quality output with minor calibration issues",
                "faithfulness_check": {
                    "score": 0.90,
                    "passed": True,
                    "citations_validated": 5,
                    "unsupported_claims": 1
                },
                "calibration_check": {
                    "score": 0.75,
                    "passed": True,
                    "confidence_alignment": "well_calibrated"
                },
                "actionability_check": {
                    "score": 0.85,
                    "passed": True,
                    "actionable_recommendations": 8,
                    "vague_recommendations": 2
                },
                "clinical_validation": {
                    "score": 0.92,
                    "passed": True,
                    "clinical_appropriateness": "high",
                    "regulatory_compliance": "compliant"
                },
                "revision_required": False,
                "approval_status": "approved"
            }
        }

    @validator("overall_quality_score")
    def validate_overall_score_consistency(cls, v, values):
        """Ensure overall score is consistent with individual check scores"""
        if all(key in values for key in ["faithfulness_check", "calibration_check", "actionability_check", "clinical_validation"]):
            individual_scores = [
                values["faithfulness_check"].score,
                values["calibration_check"].score,
                values["actionability_check"].score,
                values["clinical_validation"].score
            ]

            # Weighted average: faithfulness 30%, calibration 25%, actionability 25%, clinical 20%
            expected_score = (
                individual_scores[0] * 0.30 +
                individual_scores[1] * 0.25 +
                individual_scores[2] * 0.25 +
                individual_scores[3] * 0.20
            )

            if abs(v - expected_score) > 0.05:  # Allow small rounding differences
                raise ValueError(f"Overall score ({v}) inconsistent with individual scores (expected ~{expected_score:.2f})")

        return v

    @validator("approval_status")
    def validate_approval_consistency(cls, v, values):
        """Ensure approval status is consistent with scores and issues"""
        if "overall_quality_score" in values and "revision_required" in values:
            score = values["overall_quality_score"]
            revision_required = values["revision_required"]

            # Approval logic
            if score >= 0.85 and not revision_required:
                expected_status = "approved"
            elif score >= 0.70 and not revision_required:
                expected_status = "conditional"
            else:
                expected_status = "rejected"

            if v != expected_status:
                raise ValueError(f"Approval status ({v}) inconsistent with score ({score}) and revision requirement")

        return v

    def get_critical_issues(self) -> List[QualityIssue]:
        """Get all high-severity issues across all checks"""
        critical_issues = []

        # Collect high-severity issues from faithfulness
        critical_issues.extend([
            issue for issue in self.faithfulness_check.issues
            if issue.severity == "high"
        ])

        # Add safety concerns as critical issues
        for concern in self.clinical_validation.safety_concerns:
            critical_issues.append(QualityIssue(
                severity="high",
                issue=concern,
                location="clinical_validation",
                recommendation="Address safety concern before approval",
                category="safety"
            ))

        return critical_issues

    def generate_revision_report(self) -> Dict[str, Any]:
        """Generate comprehensive revision report"""
        critical_issues = self.get_critical_issues()

        return {
            "overall_assessment": {
                "score": self.overall_quality_score,
                "status": self.approval_status,
                "revision_required": self.revision_required
            },
            "critical_issues": [
                {
                    "issue": issue.issue,
                    "location": issue.location,
                    "recommendation": issue.recommendation,
                    "category": issue.category
                }
                for issue in critical_issues
            ],
            "improvement_priorities": [
                {
                    "priority": suggestion.priority,
                    "area": suggestion.area,
                    "suggestion": suggestion.suggestion,
                    "impact": suggestion.expected_impact
                }
                for suggestion in sorted(self.improvement_suggestions, key=lambda x: x.priority)
            ],
            "auto_revisions_available": len(self.auto_revisions),
            "next_steps": self._determine_next_steps()
        }

    def _determine_next_steps(self) -> List[str]:
        """Determine recommended next steps based on assessment"""
        next_steps = []

        if self.approval_status == "approved":
            next_steps.append("Content approved for use")
        elif self.approval_status == "conditional":
            next_steps.append("Address minor issues before final approval")
            next_steps.extend([
                f"Review {suggestion.area} improvements"
                for suggestion in self.improvement_suggestions
                if suggestion.priority in ["high", "medium"]
            ])
        else:  # rejected
            next_steps.append("Significant revision required")
            if self.auto_revisions:
                next_steps.append("Apply available auto-revisions")
            critical_issues = self.get_critical_issues()
            if critical_issues:
                next_steps.append("Address all critical issues")

        return next_steps