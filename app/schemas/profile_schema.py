from typing import List, Optional

from pydantic import BaseModel, Field


class CandidateProfileInput(BaseModel):
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
    target_roles: List[str] = Field(default_factory=list)
    available_projects: List[str] = Field(default_factory=list)
    truth_boundaries: List[str] = Field(default_factory=list)
    resume_text: str = ""
    project_context: str = ""


class CandidateProfile(CandidateProfileInput):
    id: int
    created_at: str
    updated_at: str


class ProfileSaveResponse(BaseModel):
    success: bool
    profile_id: int
    message: str


class ProfileGetResponse(BaseModel):
    success: bool
    message: str
    data: Optional[CandidateProfile] = None
