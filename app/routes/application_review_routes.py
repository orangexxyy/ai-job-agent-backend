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


@router.post(
    "",
    response_model=ApplicationReviewResponse,
    summary="规则版岗位复盘 / Rule-based application review",
    description=(
        "基于 application、JD、job_match 和可选 HR 消息生成可解释的规则复盘。"
        " / Generate an explainable rule-based review from application, JD, job match, and optional HR context."
    ),
)
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


@router.post(
    "/llm_enhance",
    response_model=ApplicationReviewLLMEnhanceResponse,
    summary="LLM 增强岗位复盘 / LLM-enhanced application review",
    description=(
        "在规则复盘基础上生成只读 LLM 增强分析；最终判断仍需用户确认。"
        " / Add read-only LLM analysis to the rule review; final decisions remain Human-in-the-loop."
    ),
)
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


@router.post(
    "/hr_reply_draft",
    response_model=ApplicationReviewReplyDraftResponse,
    summary="生成 HR 回复草稿（当前主流程） / Generate HR reply draft with application context",
    description=(
        "当前主流程的 HR 回复草稿接口。它只生成草稿，不自动发送 HR 消息，"
        "也不修改 application 状态；用户人工处理后，需要调用 "
        "POST /applications/{application_id}/confirm_hr_reply 记录状态。"
        " / Main HR reply draft endpoint. It generates a draft only, sends no message, and does not update "
        "application state. Use the confirm_hr_reply endpoint only after explicit user confirmation."
    ),
)
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
