from fastapi import APIRouter

from app.schemas.job_match_schema import JobMatchRequest, JobMatchResponse
from app.services.job_match_service import analyze_job_match


router = APIRouter(prefix="/job_match", tags=["job_match"])


@router.post("", response_model=JobMatchResponse)
def analyze_job_match_route(request: JobMatchRequest) -> JobMatchResponse:
    try:
        data = analyze_job_match(
            application_id=request.application_id,
            update_application=request.update_application,
        )
    except ValueError as exc:
        message = str(exc)
        if message == "application not found":
            return JobMatchResponse(
                success=False,
                message="application not found",
                data=None,
            )
        if message == "candidate_profile not found":
            return JobMatchResponse(
                success=False,
                message="candidate_profile not found. Please create profile first.",
                data=None,
            )
        raise

    return JobMatchResponse(
        success=True,
        message="job match analyzed",
        data=data,
    )
