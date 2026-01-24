"""
Pydantic models for structured agent responses.
Define your response schemas here for type-safe agent interactions.
"""
from typing import List, Optional, Union
from pydantic import BaseModel, Field


class IllnessInfo(BaseModel):
    """Structured response for illness identification.
    - illness_name: general name of the illness
    - type: specific type or subtype if mentioned (e.g., type 1, type 2, stage 3), otherwise null
    - subtype: specific subtype or variant if mentioned, otherwise null
    - stage: disease stage if explicitly mentioned (e.g., early, late, stage IV), otherwise null
    - anatomical_location: primary affected body part or system if mentioned, otherwise null
    - organ_touched: specific organ or tissue affected, if mentioned, otherwise null
    - category: general medical category (e.g., infectious, chronic, genetic, autoimmune)
    - severity: severity level if explicitly mentioned (mild, moderate, severe), otherwise null
    - affected_systems: list of affected body systems (e.g., respiratory, nervous, immune)
    - keywords: key medical terms (this can include types, stages, variants, etc.)
    """
    illness_name: str = Field(description="General name of the illness")
    type: Optional[str] = Field(None, description="Specific type or subtype if mentioned")
    subtype: Optional[str] = Field(None, description="Specific subtype or variant if mentioned")
    stage: Optional[str] = Field(None, description="Disease stage if explicitly mentioned")
    anatomical_location: Optional[List[str]] = Field(None, description="Primary affected body part or system if mentioned")
    organ_touched: Optional[List[str]] = Field(None, description="Specific organ or tissue affected if mentioned")
    category: str = Field(description="Medical category (e.g., chronic, acute, genetic)")
    severity: Optional[str] = Field(None, description="Severity level if mentioned")
    affected_systems: List[str] = Field(default_factory=list, description="Affected body systems")
    keywords: List[str] = Field(default_factory=list, description="Key medical terms")
    confidence_score: Optional[float] = Field(None, description="Confidence score of the identification")


class EligibilityQuestions(BaseModel):
    """Structured response for eligibility questions generation."""
    nct_id: str = Field(description="NCT ID of the clinical trial")
    inclusion_questions: List[str] = Field(default_factory=list, description="List of inclusion questions")
    exclusion_questions: List[str] = Field(default_factory=list, description="List of exclusion questions")


class ExplanationEvaluation(BaseModel):
    """Structured response for explanation evaluation."""
    comprehension_score: int = Field(
        description="Comprehension score from 0 to 100, where 100 is perfectly understandable",
        ge=0,
        le=100
    )
    is_acceptable: bool = Field(
        description="True if comprehension_score >= 60, False otherwise"
    )
    issues: List[str] = Field(
        default_factory=list,
        description="List of specific issues that make the explanation hard to understand"
    )
    suggestions: Union[str, List[str]] = Field(  # ✅ Accepte string OU liste
        default="",
        description="Specific suggestions for improving the explanation"
    )
    
    def get_suggestions_text(self) -> str:
        """Get suggestions as a single string"""
        if isinstance(self.suggestions, list):
            return "\n".join(self.suggestions)
        return self.suggestions


# ========== LOGICAL UPDATE: Graded Responses ==========

from enum import Enum
from typing import Literal

class AnswerType(str, Enum):
    """Answer types for graded responses"""
    YES = "yes"
    NO = "no"
    UNSURE = "unsure"


class GradedAnswer(BaseModel):
    """
    Simple graded answer with confidence level.
    
    Part of logical_update branch for scientific rigor.
    """
    answer: AnswerType = Field(description="Answer type (yes/no/unsure)")
    confidence: int = Field(
        ge=1, le=5,
        description="Confidence level (1=very unsure, 5=very confident)"
    )
    
    def to_score(self) -> float:
        """
        Convert to eligibility score (0.0 to 1.0)
        
        Logic:
        - YES: confidence/5 (range 0.2 to 1.0)
        - NO: 0.0 (always excluding)
        - UNSURE: 0.5 * (confidence/5)^1.5 (range 0.09 to 0.5)
          Uses quadratic modulation to amplify confidence effect:
          - Low confidence (1-2) → much lower weight
          - High confidence (4-5) → higher weight
        
        Returns:
            float: Score between 0.0 and 1.0
        """
        if self.answer == AnswerType.NO:
            return 0.0
        elif self.answer == AnswerType.YES:
            return self.confidence / 5.0
        else:  # UNSURE
            # Quadratic modulation: amplify confidence impact
            confidence_weight = (self.confidence / 5.0) ** 1.5
            return 0.5 * confidence_weight


class TrialScore(BaseModel):
    """
    Complete trial eligibility score with scientific metrics.
    
    Provides continuous scoring and categorization for objective comparison.
    """
    nct_id: str = Field(description="Clinical trial NCT ID")
    inclusion_score: float = Field(ge=0, le=1, description="Average inclusion score")
    exclusion_score: float = Field(ge=0, le=1, description="Max exclusion score")
    overall_score: float = Field(ge=0, le=1, description="Final eligibility score")
    category: Literal["Strong Match", "Potential Match", "Weak Match", "Not Eligible"] = Field(
        description="Eligibility category based on score thresholds"
    )
    uncertainty_count: int = Field(ge=0, description="Number of UNSURE responses")
    low_confidence_count: int = Field(ge=0, description="Number of responses with confidence <= 2")
    
    @classmethod
    def calculate(cls, nct_id: str, responses: dict) -> "TrialScore":
        """
        Calculate trial score from graded responses.
        
        Args:
            nct_id: Trial NCT ID
            responses: Dict mapping question_id -> GradedAnswer
        
        Returns:
            TrialScore with calculated metrics
        """
        inclusion_scores = []
        exclusion_scores = []
        uncertainty_count = 0
        low_confidence_count = 0
        
        # Process each response
        for q_id, response in responses.items():
            # Convert dict to GradedAnswer if needed
            if isinstance(response, dict):
                response = GradedAnswer(**response)
            
            score = response.to_score()
            
            # Count uncertainty metrics
            if response.answer == AnswerType.UNSURE:
                uncertainty_count += 1
            if response.confidence <= 2:
                low_confidence_count += 1
            
            # Categorize by question type (inclusion vs exclusion)
            if "_INC_" in q_id:
                inclusion_scores.append(score)
            elif "_EXC_" in q_id:
                exclusion_scores.append(score)
        
        # Calculate component scores
        inclusion_score = (
            sum(inclusion_scores) / len(inclusion_scores) 
            if inclusion_scores else 0.5
        )
        exclusion_score = max(exclusion_scores) if exclusion_scores else 0.0
        
        # Apply exclusion logic
        # If any exclusion criterion triggered (score > 0.3), patient is ineligible
        if exclusion_score > 0.3:
            overall_score = 0.0
        else:
            overall_score = inclusion_score
        
        # Categorize based on score
        if overall_score >= 0.8:
            category = "Strong Match"
        elif overall_score >= 0.6:
            category = "Potential Match"
        elif overall_score >= 0.4:
            category = "Weak Match"
        else:
            category = "Not Eligible"
        
        return cls(
            nct_id=nct_id,
            inclusion_score=inclusion_score,
            exclusion_score=exclusion_score,
            overall_score=overall_score,
            category=category,
            uncertainty_count=uncertainty_count,
            low_confidence_count=low_confidence_count
        )