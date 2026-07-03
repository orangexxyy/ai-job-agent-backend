from fastapi import APIRouter, HTTPException

from app.schemas.agent_loop_schema import AgentLoopSimulateRequest, AgentLoopSimulateResponse
from app.services.agent_loop_service import simulate_agent_loop


router = APIRouter(prefix="/agent/loop", tags=["agent"])


@router.post(
    "/simulate",
    response_model=AgentLoopSimulateResponse,
    summary="模拟 Agent 单轮决策 / Simulate one Agent loop turn",
    description="只做单轮只读模拟；不发送、不投递、不确认面试、不 book slot、不写数据库。",
)
def simulate_agent_loop_route(request: AgentLoopSimulateRequest) -> AgentLoopSimulateResponse:
    try:
        data = simulate_agent_loop(request)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return AgentLoopSimulateResponse(success=True, message="agent loop simulated", data=data)
