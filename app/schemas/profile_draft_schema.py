from typing import List, Optional

from pydantic import BaseModel, Field


class ProfileDraftReviewData(BaseModel):
    draft_exists: bool
    target_roles: List[str] = Field(default_factory=list)
    available_projects: List[str] = Field(default_factory=list)
    truth_boundaries: List[str] = Field(default_factory=list)
    expected_salary_min: Optional[int] = None
    expected_salary_max: Optional[int] = None
    minimum_salary: Optional[int] = None
    salary_note: str = ""
    availability_note: str = ""
    preferred_cities: List[str] = Field(default_factory=list)
    acceptable_cities: List[str] = Field(default_factory=list)
    relocation_policy: str = ""
    outsourcing_policy: str = ""
    onsite_policy: str = ""
    remote_policy: str = ""
    overtime_policy: str = ""
    business_trip_policy: str = ""
    resume_text_preview: str = ""
    project_context_preview: str = ""
    resume_text_length: int = 0
    project_context_length: int = 0


class ProfileDraftReviewResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ProfileDraftReviewData] = None


class ProfileDraftApplyRequest(BaseModel):
    confirmation_text: str

    class Config:
        extra = "forbid"


class ProfileDraftApplyData(BaseModel):
    applied: bool
    profile_id: Optional[int] = None
    backup_created: bool
    profile_verified: bool
    profile_apply_history_id: Optional[int] = None
    external_action_performed: bool = False


class ProfileDraftApplyResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ProfileDraftApplyData] = None
