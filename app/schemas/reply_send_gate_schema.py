from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class ReplySendGateSimulationRequest(BaseModel):
    application_id: int
    hr_message: str
    context_note: Optional[str] = None
    max_available_slots: int = Field(default=3, ge=1, le=10)


class ReplySendGateSimulationResult(BaseModel):
    application_id: int
    hr_message: str
    detected_intent: str
    proposed_action_type: str
    risk_level: str
    policy_decision: str
    reply_available: bool
    reply_candidate: Optional[str] = None
    final_safety_check_passed: bool
    final_safety_flags: List[str] = Field(default_factory=list)
    final_send_decision: str
    auto_send_simulated: bool
    requires_user_confirmation: bool
    requires_user_notification: bool
    blocked_reason: Optional[str] = None
    action_history_written: bool
    action_history_id: Optional[int] = None
    external_action_allowed: bool = False
    external_action_performed: bool = False
    debug: Dict[str, Any] = Field(default_factory=dict)


class ReplySendGateSimulationResponse(BaseModel):
    success: bool
    message: str
    data: Optional[ReplySendGateSimulationResult] = None
