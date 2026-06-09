from typing import Any, Dict, List, Optional

from pydantic import BaseModel


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
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    extra_context: Optional[str] = None


class HrReplyData(BaseModel):
    original_message: str
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    intents: List[str]
    primary_intent: str
    reply_draft: str
    safe_to_send: bool
    used_sources: List[str]
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
