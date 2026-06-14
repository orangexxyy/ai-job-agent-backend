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


class ApplicationReviewLLMEnhanceRequest(BaseModel):
    application_id: int
    hr_message: Optional[str] = None
    include_raw_prompt: bool = False


class ApplicationReviewLLMEnhanceData(BaseModel):
    application_id: int
    company_name: str
    job_title: str
    rule_review: Dict[str, Any]
    llm_enhanced_review: Optional[Dict[str, Any]] = None
    llm_used: bool = False
    llm_error: Optional[str] = None
    human_review_required: bool = True
    debug: Dict[str, Any] = Field(default_factory=dict)


class ApplicationReviewLLMEnhanceResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ApplicationReviewLLMEnhanceData] = None


class ApplicationReviewReplyDraftRequest(BaseModel):
    application_id: int
    hr_message: Optional[str] = None
    draft_tone: str = "professional"
    include_raw_prompt: bool = False


class ApplicationReviewReplyDraftData(BaseModel):
    application_id: int
    company_name: str
    job_title: str
    draft_source: str
    draft_type: str
    reply_strategy_for_user: Dict[str, Any] = Field(default_factory=dict)
    hr_reply_draft: Dict[str, Any] = Field(default_factory=dict)
    draft_text: str
    draft_goal: str
    must_confirm_before_send: List[str] = Field(default_factory=list)
    risk_notes: List[str] = Field(default_factory=list)
    safe_to_send: bool = False
    human_review_required: bool = True
    rule_review: Dict[str, Any]
    llm_enhanced_review: Optional[Dict[str, Any]] = None
    llm_used: bool = False
    llm_error: Optional[str] = None
    debug: Dict[str, Any] = Field(default_factory=dict)


class ApplicationReviewReplyDraftResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ApplicationReviewReplyDraftData] = None
