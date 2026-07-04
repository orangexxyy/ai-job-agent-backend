from fastapi import APIRouter, HTTPException

from app.schemas.auto_reply_schema import (
    AutoReplySimulationRequest,
    AutoReplySimulationResponse,
)
from app.services.auto_reply_service import simulate_supervised_auto_reply


router = APIRouter(prefix="/agent/auto_reply", tags=["agent"])


@router.post(
    "/simulate",
    response_model=AutoReplySimulationResponse,
    summary="模拟低风险 HR 回复候选 / Simulate supervised auto reply",
    description=(
        "复用 Step 20 进行只读决策，仅为安全场景生成供用户审核的候选回复；"
        "不发送、不投递、不 book slot、不写数据库、不调用 LLM。"
    ),
)
def simulate_auto_reply_route(
    request: AutoReplySimulationRequest,
) -> AutoReplySimulationResponse:
    try:
        data = simulate_supervised_auto_reply(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AutoReplySimulationResponse(
        success=True,
        message="supervised auto reply simulated",
        data=data,
    )
