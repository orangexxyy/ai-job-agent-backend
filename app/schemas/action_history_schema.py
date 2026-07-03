from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ApplicationActionHistoryItem(BaseModel):
    id: int
    application_id: Optional[int] = None
    action_type: str
    action_source: str
    before_status: Optional[str] = None
    after_status: Optional[str] = None
    before_next_action: Optional[str] = None
    after_next_action: Optional[str] = None
    user_confirmed: bool
    external_action_performed: bool
    risk_level: Optional[str] = None
    summary: str
    detail_json: Dict[str, Any] = Field(default_factory=dict)
    created_at: str


class ApplicationActionHistoryListResponse(BaseModel):
    success: bool
    message: str
    data: List[ApplicationActionHistoryItem] = Field(default_factory=list)
