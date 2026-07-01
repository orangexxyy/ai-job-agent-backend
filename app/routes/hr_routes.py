from fastapi import APIRouter

from app.schemas.hr_schema import (
    HrAnalyzeRequest,
    HrAnalyzeResponse,
    HrReplyRequest,
    HrReplyResponse,
)
from app.services.hr_intent_service import analyze_hr_message
from app.services.hr_reply_service import generate_hr_reply


router = APIRouter(prefix="/hr", tags=["hr"])


@router.post(
    "/analyze",
    response_model=HrAnalyzeResponse,
    summary="旧版 HR 意图分析接口 / Legacy HR intent analyzer",
    description=(
        "早期规则版 HR intent 接口，保留兼容，不建议作为当前 Demo 主入口。"
        " / Legacy rule-based HR intent endpoint retained for compatibility, not recommended as the main demo entry."
    ),
    deprecated=True,
)
def analyze_hr_intent(request: HrAnalyzeRequest) -> HrAnalyzeResponse:
    data = analyze_hr_message(
        message=request.message,
        company_name=request.company_name,
        job_title=request.job_title,
    )
    return HrAnalyzeResponse(
        success=True,
        message="hr message analyzed",
        data=data,
    )


@router.post(
    "/reply",
    response_model=HrReplyResponse,
    summary="旧版 HR 回复草稿接口 / Legacy HR reply draft generator",
    description=(
        "早期基础版 HR 回复草稿接口，保留兼容。当前主流程请使用 "
        "/application_review/hr_reply_draft。"
        " / Legacy HR reply draft endpoint retained for compatibility. "
        "Use /application_review/hr_reply_draft for the current demo flow."
    ),
    deprecated=True,
)
def generate_hr_reply_draft(request: HrReplyRequest) -> HrReplyResponse:
    try:
        data = generate_hr_reply(
            message=request.message,
            application_id=request.application_id,
            company_name=request.company_name,
            job_title=request.job_title,
            extra_context=request.extra_context,
        )
    except ValueError as exc:
        if str(exc) == "application not found":
            return HrReplyResponse(
                success=False,
                message="application not found",
                data=None,
            )
        raise
    if data is None:
        return HrReplyResponse(
            success=False,
            message="candidate_profile not found. Please create profile first.",
            data=None,
        )
    return HrReplyResponse(
        success=True,
        message="hr reply draft generated",
        data=data,
    )
