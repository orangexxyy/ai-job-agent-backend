from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class HrAnalyzeRequest(BaseModel):
    message: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None


class HrAnalyzeData(BaseModel):
    original_message: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    intents: List[str]
    primary_intent: str
    need_profile: bool
    need_resume_context: bool
    need_project_context: bool
    need_application_history: bool
    need_llm: bool
    risk_level: str
    matched_keywords: Dict[str, List[str]]
    suggested_next_action: str


class HrAnalyzeResponse(BaseModel):
    success: bool
    message: str
    data: HrAnalyzeData


class HrReplyRequest(BaseModel):
    message: str
    application_id: Optional[int] = None
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    extra_context: Optional[str] = None


class HrReplyData(BaseModel):
    original_message: str
    application_id: Optional[int] = None
    application_context: Optional[Dict[str, Any]] = None
    application_updated: bool = False
    application_update_fields: Dict[str, Any] = Field(default_factory=dict)
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    intents: List[str]
    primary_intent: str
    reply_draft: str
    safe_to_send: bool
    used_sources: List[str]
    context_used: List[str] = Field(default_factory=list)
    selected_context_snippets: List[Dict[str, Any]] = Field(default_factory=list)
    context_reply_mode: str = "template_only"
    truth_boundary: List[str]
    cannot_claim: List[str]
    risk_level: str
    suggested_followup: str
    agent_steps: List[str]
    debug: Dict[str, Any]


class HrReplyResponse(BaseModel):
    success: bool
    message: str
    data: Optional[HrReplyData] = None
