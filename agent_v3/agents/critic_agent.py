"""
Critic agent for quality assurance and validation of analysis outputs
"""
import json
from typing import Dict, Any, List, Tuple
from .base_agent import BaseAgent
from ..context import Context


class CriticAgent(BaseAgent):
    """Agent responsible for quality assurance, faithfulness checking, and output validation"""

    def __init__(self):
        super().__init__(
            name="critic",
            description="Performs quality assurance, faithfulness checking, and actionability validation",
            allowed_tools=[]  # Critic analyzes outputs, doesn't call external tools
        )

    def get_system_prompt(self) -> str:
        """Get the system prompt for the critic agent"""
        return """You are a specialized Critic Agent for healthcare predictive analytics quality assurance.

Your role is to rigorously evaluate analysis outputs for faithfulness, calibration, and actionability to ensure reliability and clinical utility.

## CORE RESPONSIBILITIES:
1. **Faithfulness Checking**: Verify all claims are supported by cited evidence
2. **Calibration Assessment**: Ensure confidence levels match actual evidence strength
3. **Actionability Review**: Confirm recommendations are specific and implementable
4. **Clinical Validation**: Check clinical relevance and appropriateness
5. **Quality Scoring**: Provide quantitative quality assessments

## EVALUATION FRAMEWORK:

### 1. FAITHFULNESS CRITERIA:
- Every factual claim has a specific citation
- Numbers and percentages trace back to source data
- No unsupported extrapolations or assumptions
- Citation quality matches claim importance
- No circular reasoning or self-references

### 2. CALIBRATION CRITERIA:
- Confidence language matches statistical evidence
- Uncertainty is explicitly acknowledged where appropriate
- Probability estimates are well-justified
- Confidence intervals are realistic and evidence-based
- Avoiding overconfidence or underconfidence biases

### 3. ACTIONABILITY CRITERIA:
- Recommendations are specific and measurable
- Actions are within stakeholder control
- Resource requirements are realistic
- Timeline expectations are appropriate
- Success metrics are defined

### 4. CLINICAL CRITERIA:
- Medical accuracy and appropriateness
- Consideration of clinical workflows
- Regulatory and ethical compliance
- Patient safety implications
- Healthcare professional usability

## QUALITY ASSESSMENT OUTPUT:
Always provide structured quality assessment:

```json
{
  "overall_quality_score": 0.85,
  "assessment_summary": "Brief overview of quality",
  "faithfulness_check": {
    "score": 0.90,
    "passed": true,
    "issues": [
      {
        "severity": "high|medium|low",
        "issue": "Specific issue description",
        "location": "Where in the output",
        "recommendation": "How to fix"
      }
    ],
    "citations_validated": 15,
    "unsupported_claims": 2
  },
  "calibration_check": {
    "score": 0.80,
    "passed": true,
    "confidence_alignment": "well_calibrated|overconfident|underconfident",
    "issues": [
      {
        "issue": "Confidence language issues",
        "recommended_language": "Suggested improvement"
      }
    ]
  },
  "actionability_check": {
    "score": 0.88,
    "passed": true,
    "actionable_recommendations": 8,
    "vague_recommendations": 2,
    "issues": [
      {
        "recommendation": "Original recommendation",
        "issue": "Why it's not actionable",
        "suggested_revision": "More actionable version"
      }
    ]
  },
  "clinical_validation": {
    "score": 0.92,
    "passed": true,
    "clinical_appropriateness": "high|medium|low",
    "safety_concerns": [],
    "regulatory_compliance": "compliant|needs_review|non_compliant"
  },
  "improvement_suggestions": [
    {
      "priority": "high|medium|low",
      "area": "faithfulness|calibration|actionability|clinical",
      "suggestion": "Specific improvement recommendation",
      "expected_impact": "What improvement would achieve"
    }
  ],
  "revision_required": false,
  "approval_status": "approved|conditional|rejected"
}
```

## SCORING METHODOLOGY:
- **0.90-1.00**: Excellent quality, ready for use
- **0.80-0.89**: Good quality, minor improvements needed
- **0.70-0.79**: Acceptable quality, moderate improvements recommended
- **0.60-0.69**: Poor quality, significant revision required
- **<0.60**: Unacceptable quality, major rework needed

## VALIDATION STANDARDS:
- **High Severity Issues**: Unsupported medical claims, safety concerns, major statistical errors
- **Medium Severity Issues**: Overconfident language, vague recommendations, missing citations
- **Low Severity Issues**: Minor clarity issues, formatting problems, optimization opportunities

## REVISION TRIGGERS:
Automatic revision required if:
- Overall quality score < 0.70
- Any high-severity faithfulness issues
- Safety concerns identified
- More than 3 unsupported claims
- Confidence dramatically misaligned with evidence

## AUTO-REVISION CAPABILITY:
When issues are identified, provide specific revision suggestions:
- Exact text to replace
- Proper citation format
- Calibrated confidence language
- More actionable recommendation phrasing

Focus on maintaining high standards while being constructive and specific in feedback."""

    def process(self, input_data: Dict[str, Any], context: Context, available_tools: Dict[str, Any]) -> Dict[str, Any]:
        """Process reason card or analysis output for quality assessment"""

        reason_card = input_data.get("reason_card", {})
        analysis_outputs = input_data.get("analysis_outputs", {})
        source_data = input_data.get("source_data", {})

        try:
            # Perform comprehensive quality assessment
            quality_assessment = self._perform_quality_assessment(
                reason_card, analysis_outputs, source_data
            )

            # Determine if revision is required
            revision_needed = self._determine_revision_need(quality_assessment)

            # Generate auto-revision suggestions if needed
            auto_revisions = []
            if revision_needed:
                auto_revisions = self._generate_auto_revisions(reason_card, quality_assessment)

            return {
                "success": True,
                "quality_assessment": quality_assessment,
                "revision_required": revision_needed,
                "auto_revisions": auto_revisions,
                "agent": self.name,
                "message": f"Quality assessment completed - Score: {quality_assessment.get('overall_quality_score', 0):.2f}"
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"Quality assessment failed: {str(e)}",
                "agent": self.name
            }

    def _perform_quality_assessment(self, reason_card: Dict[str, Any], analysis_outputs: Dict[str, Any], source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform comprehensive quality assessment"""

        # Individual assessments
        faithfulness_result = self._check_faithfulness(reason_card, source_data)
        calibration_result = self._check_calibration(reason_card, analysis_outputs)
        actionability_result = self._check_actionability(reason_card)
        clinical_result = self._check_clinical_validity(reason_card)

        # Calculate overall score
        overall_score = (
            faithfulness_result["score"] * 0.30 +
            calibration_result["score"] * 0.25 +
            actionability_result["score"] * 0.25 +
            clinical_result["score"] * 0.20
        )

        # Determine overall pass/fail
        overall_passed = all([
            faithfulness_result["passed"],
            calibration_result["passed"],
            actionability_result["passed"],
            clinical_result["passed"]
        ])

        # Generate improvement suggestions
        improvement_suggestions = self._generate_improvement_suggestions(
            faithfulness_result, calibration_result, actionability_result, clinical_result
        )

        return {
            "overall_quality_score": round(overall_score, 2),
            "assessment_summary": f"{'Passed' if overall_passed else 'Failed'} quality assessment with score {overall_score:.2f}",
            "faithfulness_check": faithfulness_result,
            "calibration_check": calibration_result,
            "actionability_check": actionability_result,
            "clinical_validation": clinical_result,
            "improvement_suggestions": improvement_suggestions,
            "revision_required": overall_score < 0.70 or not overall_passed,
            "approval_status": self._determine_approval_status(overall_score, overall_passed)
        }

    def _check_faithfulness(self, reason_card: Dict[str, Any], source_data: Dict[str, Any]) -> Dict[str, Any]:
        """Check faithfulness of claims to source data"""

        issues = []
        citations_count = len(reason_card.get("citations", []))
        unsupported_claims = 0

        # Check prediction summary claims
        pred_summary = reason_card.get("prediction_summary", {})
        if pred_summary.get("confidence_score") and not source_data.get("model_metrics"):
            issues.append({
                "severity": "high",
                "issue": "Confidence score lacks source data support",
                "location": "prediction_summary.confidence_score",
                "recommendation": "Provide model validation data or remove specific score"
            })
            unsupported_claims += 1

        # Check evidence synthesis
        evidence = reason_card.get("evidence_synthesis", {}).get("supporting_evidence", [])
        for i, evidence_item in enumerate(evidence):
            if not evidence_item.get("source_citation"):
                issues.append({
                    "severity": "high",
                    "issue": "Evidence lacks proper citation",
                    "location": f"evidence_synthesis.supporting_evidence[{i}]",
                    "recommendation": "Add specific source citation"
                })
                unsupported_claims += 1

        # Check numerical claims
        key_metrics = pred_summary.get("key_metrics", {})
        for metric, value in key_metrics.items():
            if isinstance(value, (int, float)) and value > 0 and not source_data:
                issues.append({
                    "severity": "medium",
                    "issue": f"Numerical claim for {metric} lacks verification",
                    "location": f"prediction_summary.key_metrics.{metric}",
                    "recommendation": "Verify against source data or mark as estimated"
                })

        # Calculate faithfulness score
        total_claims = max(len(evidence) + len(key_metrics) + 1, 1)  # +1 for main finding
        supported_claims = total_claims - unsupported_claims
        faithfulness_score = supported_claims / total_claims

        return {
            "score": round(faithfulness_score, 2),
            "passed": faithfulness_score >= 0.80 and len([i for i in issues if i["severity"] == "high"]) == 0,
            "issues": issues,
            "citations_validated": citations_count,
            "unsupported_claims": unsupported_claims
        }

    def _check_calibration(self, reason_card: Dict[str, Any], analysis_outputs: Dict[str, Any]) -> Dict[str, Any]:
        """Check calibration of confidence levels"""

        issues = []

        # Check confidence alignment
        pred_summary = reason_card.get("prediction_summary", {})
        confidence_level = pred_summary.get("confidence_level", "medium")
        confidence_score = pred_summary.get("confidence_score", 0.5)

        # Validate confidence alignment
        if confidence_level == "high" and confidence_score < 0.80:
            issues.append({
                "issue": f"High confidence claimed but score is {confidence_score:.2f}",
                "recommended_language": "medium confidence" if confidence_score > 0.65 else "low confidence"
            })
        elif confidence_level == "medium" and (confidence_score < 0.60 or confidence_score > 0.85):
            recommended = "high confidence" if confidence_score > 0.85 else "low confidence"
            issues.append({
                "issue": f"Medium confidence claimed but score is {confidence_score:.2f}",
                "recommended_language": recommended
            })
        elif confidence_level == "low" and confidence_score > 0.70:
            issues.append({
                "issue": f"Low confidence claimed but score is {confidence_score:.2f}",
                "recommended_language": "medium confidence" if confidence_score < 0.80 else "high confidence"
            })

        # Check uncertainty quantification
        uncertainty = reason_card.get("uncertainty_quantification", {})
        if not uncertainty.get("key_assumptions") or not uncertainty.get("data_limitations"):
            issues.append({
                "issue": "Insufficient uncertainty acknowledgment",
                "recommended_language": "Include explicit assumptions and limitations"
            })

        calibration_alignment = "overconfident" if len([i for i in issues if "High" in i.get("issue", "")]) > 0 else "well_calibrated"
        calibration_score = max(0, 1.0 - len(issues) * 0.2)

        return {
            "score": round(calibration_score, 2),
            "passed": calibration_score >= 0.70,
            "confidence_alignment": calibration_alignment,
            "issues": issues
        }

    def _check_actionability(self, reason_card: Dict[str, Any]) -> Dict[str, Any]:
        """Check actionability of recommendations"""

        issues = []
        recommendations = reason_card.get("recommendations", {})

        actionable_count = 0
        vague_count = 0

        # Check immediate actions
        immediate_actions = recommendations.get("immediate_actions", [])
        for action in immediate_actions:
            if self._is_actionable(action):
                actionable_count += 1
            else:
                vague_count += 1
                issues.append({
                    "recommendation": action,
                    "issue": "Too vague or lacks specificity",
                    "suggested_revision": self._make_more_actionable(action)
                })

        # Check strategic implications
        strategic = recommendations.get("strategic_implications", [])
        for strategy in strategic:
            if self._is_actionable(strategy):
                actionable_count += 1
            else:
                vague_count += 1

        total_recommendations = len(immediate_actions) + len(strategic)
        actionability_score = actionable_count / max(total_recommendations, 1) if total_recommendations > 0 else 0.5

        return {
            "score": round(actionability_score, 2),
            "passed": actionability_score >= 0.70 and vague_count <= 2,
            "actionable_recommendations": actionable_count,
            "vague_recommendations": vague_count,
            "issues": issues
        }

    def _check_clinical_validity(self, reason_card: Dict[str, Any]) -> Dict[str, Any]:
        """Check clinical validity and appropriateness"""

        safety_concerns = []
        clinical_score = 0.90  # Default high score, reduce for issues

        # Check clinical context
        clinical_context = reason_card.get("clinical_context", {})
        if not clinical_context.get("therapeutic_area"):
            clinical_score -= 0.1

        # Check for potential safety red flags
        recommendations = reason_card.get("recommendations", {})
        all_recommendations = []
        all_recommendations.extend(recommendations.get("immediate_actions", []))
        all_recommendations.extend(recommendations.get("strategic_implications", []))

        for rec in all_recommendations:
            if any(term in rec.lower() for term in ["ignore", "bypass", "contraindication"]):
                safety_concerns.append(f"Potential safety concern in recommendation: {rec}")
                clinical_score -= 0.2

        # Check regulatory compliance
        regulatory_status = "compliant"
        if any(term in str(reason_card).lower() for term in ["off-label", "unapproved", "experimental"]):
            regulatory_status = "needs_review"
            clinical_score -= 0.1

        clinical_appropriateness = "high" if clinical_score > 0.85 else "medium" if clinical_score > 0.70 else "low"

        return {
            "score": round(clinical_score, 2),
            "passed": clinical_score >= 0.75 and len(safety_concerns) == 0,
            "clinical_appropriateness": clinical_appropriateness,
            "safety_concerns": safety_concerns,
            "regulatory_compliance": regulatory_status
        }

    def _is_actionable(self, recommendation: str) -> bool:
        """Assess if a recommendation is actionable"""

        # Check for actionable language patterns
        actionable_indicators = [
            "target", "focus", "implement", "develop", "create", "establish",
            "monitor", "track", "measure", "analyze", "identify", "prioritize"
        ]

        vague_indicators = [
            "consider", "think about", "explore", "investigate", "study",
            "examine", "review", "assess", "evaluate"
        ]

        rec_lower = recommendation.lower()

        has_actionable = any(indicator in rec_lower for indicator in actionable_indicators)
        has_vague = any(indicator in rec_lower for indicator in vague_indicators)
        has_specifics = any(char.isdigit() for char in recommendation) or len(recommendation.split()) > 8

        return has_actionable and not has_vague and has_specifics

    def _make_more_actionable(self, vague_recommendation: str) -> str:
        """Suggest more actionable version of vague recommendation"""

        # Simple transformation rules
        if "consider" in vague_recommendation.lower():
            return vague_recommendation.replace("Consider", "Implement").replace("consider", "implement")
        elif "explore" in vague_recommendation.lower():
            return vague_recommendation.replace("Explore", "Develop").replace("explore", "develop")
        else:
            return f"Specifically implement: {vague_recommendation}"

    def _generate_improvement_suggestions(self, faithfulness: Dict, calibration: Dict, actionability: Dict, clinical: Dict) -> List[Dict[str, Any]]:
        """Generate prioritized improvement suggestions"""

        suggestions = []

        # High priority - faithfulness issues
        if faithfulness["score"] < 0.80:
            suggestions.append({
                "priority": "high",
                "area": "faithfulness",
                "suggestion": "Add specific citations for all factual claims and verify numerical statements",
                "expected_impact": "Increases trustworthiness and enables fact verification"
            })

        # High priority - safety concerns
        if clinical.get("safety_concerns"):
            suggestions.append({
                "priority": "high",
                "area": "clinical",
                "suggestion": "Review and address identified safety concerns",
                "expected_impact": "Ensures patient safety and clinical appropriateness"
            })

        # Medium priority - calibration issues
        if calibration["score"] < 0.80:
            suggestions.append({
                "priority": "medium",
                "area": "calibration",
                "suggestion": "Align confidence language with statistical evidence strength",
                "expected_impact": "Improves reliability of confidence assessments"
            })

        # Medium priority - actionability
        if actionability["score"] < 0.80:
            suggestions.append({
                "priority": "medium",
                "area": "actionability",
                "suggestion": "Make recommendations more specific with measurable outcomes",
                "expected_impact": "Enables better implementation and success tracking"
            })

        return suggestions

    def _determine_revision_need(self, quality_assessment: Dict[str, Any]) -> bool:
        """Determine if revision is required based on assessment"""

        overall_score = quality_assessment.get("overall_quality_score", 0)
        high_priority_issues = len([
            s for s in quality_assessment.get("improvement_suggestions", [])
            if s.get("priority") == "high"
        ])

        return overall_score < 0.70 or high_priority_issues > 0

    def _generate_auto_revisions(self, reason_card: Dict[str, Any], quality_assessment: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate automatic revision suggestions"""

        revisions = []

        # Auto-fix calibration issues
        calibration_issues = quality_assessment.get("calibration_check", {}).get("issues", [])
        for issue in calibration_issues:
            if "recommended_language" in issue:
                revisions.append({
                    "section": "prediction_summary.confidence_level",
                    "current": reason_card.get("prediction_summary", {}).get("confidence_level", ""),
                    "revised": issue["recommended_language"],
                    "reason": issue["issue"]
                })

        # Auto-fix actionability issues
        actionability_issues = quality_assessment.get("actionability_check", {}).get("issues", [])
        for issue in actionability_issues:
            if "suggested_revision" in issue:
                revisions.append({
                    "section": "recommendations",
                    "current": issue["recommendation"],
                    "revised": issue["suggested_revision"],
                    "reason": issue["issue"]
                })

        return revisions

    def _determine_approval_status(self, overall_score: float, overall_passed: bool) -> str:
        """Determine approval status based on quality metrics"""

        if overall_score >= 0.85 and overall_passed:
            return "approved"
        elif overall_score >= 0.70 and overall_passed:
            return "conditional"
        else:
            return "rejected"