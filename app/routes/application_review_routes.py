from fastapi import APIRouter

from app.schemas.application_review_schema import (
    ApplicationReviewRequest,
    ApplicationReviewResponse,
)
from app.services.application_review_service import review_application


router = APIRouter(prefix="/application_review", tags=["application_review"])


@router.post("", response_model=ApplicationReviewResponse)
def review_application_route(
    request: ApplicationReviewRequest,
) -> ApplicationReviewResponse:
    try:
        data = review_application(
            application_id=request.application_id,
            hr_message=request.hr_message,
            update_application=request.update_application,
        )
    except ValueError as exc:
        if str(exc) == "application not found":
            return ApplicationReviewResponse(
                success=False,
                message="application not found",
                data=None,
            )
        raise

    return ApplicationReviewResponse(
        success=True,
        message="application reviewed",
        data=data,
    )
