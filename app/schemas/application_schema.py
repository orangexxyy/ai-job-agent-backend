from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


VALID_APPLICATION_STATUSES = {
    "saved",
    "applied",
    "hr_contacted",
    "hr_replied",
    "interview_scheduled",
    "interview_done",
    "offer",
    "rejected",
    "closed",
}


class ApplicationCreateRequest(BaseModel):
    company_name: str
    job_title: str
    source: Optional[str] = None
    job_source: str = ""
    job_url: str = ""
    jd_text: str = ""
    status: str = "saved"
    match_score: Optional[int] = None
    hr_contact_name: str = ""
    hr_contact_channel: str = ""
    last_hr_message: str = ""
    next_action: str = ""
    next_action_due_date: str = ""
    notes: str = ""
    risk_flags: List[str] = Field(default_factory=list)


class ApplicationUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    job_title: Optional[str] = None
    source: Optional[str] = None
    job_source: Optional[str] = None
    job_url: Optional[str] = None
    jd_text: Optional[str] = None
    status: Optional[str] = None
    match_score: Optional[int] = None
    hr_contact_name: Optional[str] = None
    hr_contact_channel: Optional[str] = None
    last_hr_message: Optional[str] = None
    next_action: Optional[str] = None
    next_action_due_date: Optional[str] = None
    notes: Optional[str] = None
    risk_flags: Optional[List[str]] = None


class ApplicationHrReplyConfirmRequest(BaseModel):
    draft_text: str = Field(min_length=1)
    hr_message: Optional[str] = None
    sent_channel: Literal["manual"] = "manual"
    next_action: str = Field(default="wait_for_hr_response", min_length=1)
    note: str = ""


class ApplicationItem(ApplicationCreateRequest):
    id: int
    source_type: str = ""
    jd_summary: str = ""
    jd_keywords: List[str] = Field(default_factory=list)
    jd_required_skills: List[str] = Field(default_factory=list)
    jd_years_requirement: str = ""
    jd_location_requirement: str = ""
    jd_remote_type: str = "unknown"
    created_at: str
    updated_at: str


class ApplicationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ApplicationItem] = None


class ApplicationListResponse(BaseModel):
    success: bool
    message: str
    data: List[ApplicationItem]


class ApplicationHrReplyConfirmData(BaseModel):
    application_id: int
    status: str
    next_action: str
    sent_channel: str
    confirmation_recorded: bool
    already_confirmed: bool = False
    application: ApplicationItem
    debug: Dict[str, Any] = Field(default_factory=dict)


class ApplicationHrReplyConfirmResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ApplicationHrReplyConfirmData] = None
