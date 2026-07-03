from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AutomationPolicyRequest(BaseModel):
    application_id: Optional[int] = None
    hr_message: str = ""
    proposed_action_type: str
    draft_text: Optional[str] = None
    context_note: Optional[str] = None


class AutomationPolicyDecision(BaseModel):
    application_id: Optional[int] = None
    proposed_action_type: str
    risk_level: str
    policy_decision: str
    agent_can_handle: bool
    requires_user_confirmation: bool
    requires_user_notification: bool
    external_action_allowed: bool = False
    reasons: List[str] = Field(default_factory=list)
    blocked_by: List[str] = Field(default_factory=list)
    preference_risk_flags: List[str] = Field(default_factory=list)
    suggested_next_step: str
    debug: Dict[str, Any] = Field(default_factory=dict)


class AutomationPolicyResponse(BaseModel):
    success: bool
    message: str
    data: Optional[AutomationPolicyDecision] = None
