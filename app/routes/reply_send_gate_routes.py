from fastapi import APIRouter, HTTPException

from app.schemas.reply_send_gate_schema import (
    ReplySendGateSimulationRequest,
    ReplySendGateSimulationResponse,
)
from app.services.reply_send_gate_service import simulate_reply_send_gate


router = APIRouter(prefix="/agent/reply_send_gate", tags=["agent"])


@router.post(
    "/simulate",
    response_model=ReplySendGateSimulationResponse,
    summary="模拟最终回复发送门禁 / Simulate final reply send gate",
    description=(
        "复用 Step 21 并执行最终文本安全检查；通过时只记录 simulated send history，"
        "不执行真实发送、投递、附件上传、slot booking 或平台操作。"
    ),
)
def simulate_reply_send_gate_route(
    request: ReplySendGateSimulationRequest,
) -> ReplySendGateSimulationResponse:
    try:
        data = simulate_reply_send_gate(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ReplySendGateSimulationResponse(
        success=True,
        message="reply send gate simulated",
        data=data,
    )
