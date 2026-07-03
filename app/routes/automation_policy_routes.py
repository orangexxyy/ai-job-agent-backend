from fastapi import APIRouter, HTTPException

from app.schemas.automation_policy_schema import (
    AutomationPolicyRequest,
    AutomationPolicyResponse,
)
from app.services.automation_policy_service import evaluate_automation_policy


router = APIRouter(prefix="/agent/automation_policy", tags=["agent"])


@router.post(
    "/evaluate",
    response_model=AutomationPolicyResponse,
    summary="评估 Agent 动作权限 / Evaluate automation policy for an Agent action",
    description=(
        "只做规则策略判断，用于后续 Agent Loop 前置决策；不执行外部动作，"
        "不发送 HR 消息、不投递、不确认面试。external_action_allowed 始终为 false。"
        " / Evaluate an action with rules only. No external action, message, application, "
        "or interview confirmation is performed."
    ),
)
def evaluate_automation_policy_route(
    request: AutomationPolicyRequest,
) -> AutomationPolicyResponse:
    try:
        data = evaluate_automation_policy(request)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return AutomationPolicyResponse(
        success=True,
        message="automation policy evaluated",
        data=data,
    )
