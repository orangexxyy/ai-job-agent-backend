from typing import List, Optional

from pydantic import BaseModel, Field


VALID_APPLICATION_STATUSES = {
    "saved",
    "applied",
    "hr_contacted",
    "interview_scheduled",
    "interview_done",
    "offer",
    "rejected",
    "closed",
}


class ApplicationCreateRequest(BaseModel):
    company_name: str
    job_title: str
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


class ApplicationItem(ApplicationCreateRequest):
    id: int
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
