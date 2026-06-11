from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class JobMatchRequest(BaseModel):
    application_id: int
    update_application: bool = True


class JobMatchDimension(BaseModel):
    name: str
    score: int
    max_score: int
    matched_signals: List[str] = Field(default_factory=list)
    missing_signals: List[str] = Field(default_factory=list)


class JobMatchData(BaseModel):
    application_id: int
    company_name: str
    job_title: str
    match_score: int
    match_level: str
    recommendation: str
    dimensions: List[JobMatchDimension]
    matched_signals: List[str] = Field(default_factory=list)
    missing_signals: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    suggested_next_action: str
    application_updated: bool = False
    application_update_fields: Dict[str, Any] = Field(default_factory=dict)
    debug: Dict[str, Any] = Field(default_factory=dict)


class JobMatchResponse(BaseModel):
    success: bool
    message: str
    data: Optional[JobMatchData] = None
