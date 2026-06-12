from fastapi import APIRouter

from app.schemas.agent_schema import WorkflowPreviewRequest, WorkflowPreviewResponse
from app.services.workflow_service import run_workflow_preview


router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/workflow_preview", response_model=WorkflowPreviewResponse)
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
