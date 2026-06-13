from fastapi import APIRouter

from app.schemas.application_review_schema import (
    ApplicationReviewLLMEnhanceRequest,
    ApplicationReviewLLMEnhanceResponse,
    ApplicationReviewRequest,
    ApplicationReviewResponse,
)
from app.services.application_review_llm_service import (
    enhance_application_review_with_llm,
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


@router.post("/llm_enhance", response_model=ApplicationReviewLLMEnhanceResponse)
def enhance_application_review_route(
    request: ApplicationReviewLLMEnhanceRequest,
) -> ApplicationReviewLLMEnhanceResponse:
    try:
        data = enhance_application_review_with_llm(
            application_id=request.application_id,
            hr_message=request.hr_message,
            include_raw_prompt=request.include_raw_prompt,
        )
    except ValueError as exc:
        if str(exc) == "application not found":
            return ApplicationReviewLLMEnhanceResponse(
                success=False,
                message="application not found",
                data=None,
            )
        raise

    message = "llm enhanced review generated"
    if data.get("llm_error"):
        message = data["llm_error"]
    return ApplicationReviewLLMEnhanceResponse(
        success=True,
        message=message,
        data=data,
    )
