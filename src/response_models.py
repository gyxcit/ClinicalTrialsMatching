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