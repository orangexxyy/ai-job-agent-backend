from fastapi import APIRouter

from app.schemas.agent_schema import WorkflowPreviewRequest, WorkflowPreviewResponse
from app.services.langgraph_workflow_service import run_langgraph_workflow_preview
from app.services.workflow_service import run_workflow_preview


router = APIRouter(prefix="/agent", tags=["agent"])


@router.post(
    "/workflow_preview",
    response_model=WorkflowPreviewResponse,
    summary="旧版 Agent 工作流预览 / Legacy agent workflow preview",
    description=(
        "早期普通 Python workflow preview，保留兼容。当前主流程请使用 "
        "/agent/langgraph_workflow_preview。"
        " / Legacy Python workflow preview retained for compatibility. Use the LangGraph preview for the current demo flow."
    ),
    deprecated=True,
)
def workflow_preview_route(
    request: WorkflowPreviewRequest,
) -> WorkflowPreviewResponse:
    try:
        data = run_workflow_preview(
            application_id=request.application_id,
            hr_message=request.hr_message,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "application not found":
            return WorkflowPreviewResponse(
                success=False,
                message="application not found",
                data=None,
            )
        if message == "candidate_profile not found":
            return WorkflowPreviewResponse(
                success=False,
                message="candidate_profile not found. Please create profile first.",
                data=None,
            )
        raise

    return WorkflowPreviewResponse(
        success=True,
        message="workflow preview generated",
        data=data,
    )


@router.post(
    "/langgraph_workflow_preview",
    response_model=WorkflowPreviewResponse,
    summary="LangGraph 工作流预览 / LangGraph workflow preview",
    description=(
        "预览 LangGraph 的 node、edge、state 和人工审批边界。"
        "该接口不自动发送、不自动投递、不自动确认面试。"
        " / Preview LangGraph nodes, edges, state, and human approval boundaries. "
        "It does not send messages, apply to jobs, or confirm interviews automatically."
    ),
)
def langgraph_workflow_preview_route(
    request: WorkflowPreviewRequest,
) -> WorkflowPreviewResponse:
    try:
        data = run_langgraph_workflow_preview(
            application_id=request.application_id,
            hr_message=request.hr_message,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "application not found":
            return WorkflowPreviewResponse(
                success=False,
                message="application not found",
                data=None,
            )
        if message == "candidate_profile not found":
            return WorkflowPreviewResponse(
                success=False,
                message="candidate_profile not found. Please create profile first.",
                data=None,
            )
        raise

    return WorkflowPreviewResponse(
        success=True,
        message="langgraph workflow preview generated",
        data=data,
    )
