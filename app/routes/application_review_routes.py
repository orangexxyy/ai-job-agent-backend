from fastapi import APIRouter

from app.schemas.application_review_schema import (
    ApplicationReviewLLMEnhanceRequest,
    ApplicationReviewLLMEnhanceResponse,
    ApplicationReviewReplyDraftRequest,
    ApplicationReviewReplyDraftResponse,
    ApplicationReviewRequest,
    ApplicationReviewResponse,
)
from app.services.application_review_llm_service import (
    enhance_application_review_with_llm,
)
from app.services.application_review_service import review_application
from app.services.hr_reply_draft_llm_service import (
    generate_hr_reply_draft_from_review,
)


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


@router.post("/hr_reply_draft", response_model=ApplicationReviewReplyDraftResponse)
def generate_hr_reply_draft_route(
    request: ApplicationReviewReplyDraftRequest,
) -> ApplicationReviewReplyDraftResponse:
    try:
        data = generate_hr_reply_draft_from_review(
            application_id=request.application_id,
            hr_message=request.hr_message,
            draft_tone=request.draft_tone,
            include_raw_prompt=request.include_raw_prompt,
        )
    except ValueError as exc:
        if str(exc) == "application not found":
            return ApplicationReviewReplyDraftResponse(
                success=False,
                message="application not found",
                data=None,
            )
        raise

    return ApplicationReviewReplyDraftResponse(
        success=True,
        message="HR reply draft generated",
        data=data,
    )
