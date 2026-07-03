from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from app.schemas.automation_policy_schema import AutomationPolicyDecision


class AgentLoopSimulateRequest(BaseModel):
    application_id: int
    hr_message: str
    context_note: Optional[str] = None
    max_available_slots: int = Field(default=3, ge=1, le=10)


class AgentLoopSimulateResult(BaseModel):
    application_id: int
    hr_message: str
    observation: Dict[str, Any]
    detected_intent: str
    proposed_action_type: str
    policy: AutomationPolicyDecision
    agent_loop_decision: str
    simulated_next_step: str
    simulated_tool_plan: List[Dict[str, Any]] = Field(default_factory=list)
    recommended_reply_strategy: str
    available_slots_preview: List[Dict[str, Any]] = Field(default_factory=list)
    requires_user_confirmation: bool
    requires_user_notification: bool
    external_action_allowed: bool = False
    debug: Dict[str, Any] = Field(default_factory=dict)


class AgentLoopSimulateResponse(BaseModel):
    success: bool
    message: str
    data: Optional[AgentLoopSimulateResult] = None
