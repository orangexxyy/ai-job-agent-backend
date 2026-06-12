from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class WorkflowPreviewRequest(BaseModel):
    application_id: int
    hr_message: Optional[str] = None


class WorkflowStep(BaseModel):
    name: str
    status: str
    summary: str


class WorkflowStateSummary(BaseModel):
    has_candidate_profile: bool
    has_application: bool
    has_hr_message: bool
    match_level: Optional[str] = None
    primary_intent: Optional[str] = None
    reply_draft_generated: bool = False


class WorkflowPreviewData(BaseModel):
    workflow_mode: str
    workflow_engine: Optional[str] = None
    application_id: int
    company_name: str
    job_title: str
    workflow_steps: List[WorkflowStep] = Field(default_factory=list)
    state_summary: WorkflowStateSummary
    job_match: Dict[str, Any]
    hr_intent: Optional[Dict[str, Any]] = None
    hr_reply: Optional[Dict[str, Any]] = None
    approval_required: bool
    approved_by_user: bool
    next_action: str
    debug: Dict[str, Any] = Field(default_factory=dict)


class WorkflowPreviewResponse(BaseModel):
    success: bool
    message: str
    data: Optional[WorkflowPreviewData] = None
