from typing import Dict, Optional

from pydantic import BaseModel, Field


class ProfileApplyHistoryItem(BaseModel):
    id: int
    draft_path: str
    backup_path: Optional[str] = None
    profile_verified: bool
    user_confirmed: bool
    external_action_performed: bool
    detail_json: Dict[str, int] = Field(default_factory=dict)
    created_at: str
