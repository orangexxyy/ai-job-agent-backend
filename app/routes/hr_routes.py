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


@router.post("/analyze", response_model=HrAnalyzeResponse)
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


@router.post("/reply", response_model=HrReplyResponse)
def generate_hr_reply_draft(request: HrReplyRequest) -> HrReplyResponse:
    data = generate_hr_reply(
        message=request.message,
        company_name=request.company_name,
        job_title=request.job_title,
        extra_context=request.extra_context,
    )
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
