from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AutoReplySimulationRequest(BaseModel):
    application_id: int
    hr_message: str
    context_note: Optional[str] = None
    max_available_slots: int = Field(default=3, ge=1, le=10)


class AutoReplySimulationResult(BaseModel):
    application_id: int
    hr_message: str
    detected_intent: str
    proposed_action_type: str
    agent_loop_decision: str
    risk_level: str
    policy_decision: str
    reply_strategy: str
    reply_candidate: Optional[str] = None
    reply_available: bool
    requires_user_confirmation: bool
    requires_user_notification: bool
    external_action_allowed: bool = False
    blocked_reason: Optional[str] = None
    safety_notes: List[str] = Field(default_factory=list)
    debug: Dict[str, Any] = Field(default_factory=dict)


class AutoReplySimulationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[AutoReplySimulationResult] = None
