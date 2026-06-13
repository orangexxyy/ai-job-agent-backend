from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApplicationReviewRequest(BaseModel):
    application_id: int
    hr_message: Optional[str] = None
    update_application: bool = False


class ApplicationReviewData(BaseModel):
    application_id: int
    company_name: str
    job_title: str
    review_mode: str = "rule_based"
    review_score: int
    review_level: str
    confidence: str
    recommended_action: str
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    reasons: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    missing_information: List[str] = Field(default_factory=list)
    suggested_next_message_type: str
    human_review_required: bool = True
    job_match: Dict[str, Any] = Field(default_factory=dict)
    hr_intent: Optional[Dict[str, Any]] = None
    decision_factors: Dict[str, Any] = Field(default_factory=dict)
    llm_ready_context: Dict[str, Any] = Field(default_factory=dict)
    llm_used: bool = False
    debug: Dict[str, Any] = Field(default_factory=dict)


class ApplicationReviewResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ApplicationReviewData] = None
