from fastapi import APIRouter

from app.schemas.profile_schema import (
    CandidateProfileInput,
    ProfileGetResponse,
    ProfileSaveResponse,
)
from app.services.profile_service import get_candidate_profile, save_candidate_profile


router = APIRouter(tags=["profile"])


@router.post(
    "/profile",
    response_model=ProfileSaveResponse,
    summary="保存候选人档案 / Save candidate profile",
    description=(
        "保存 candidate_profile，作为岗位分析和 HR 回复的候选人事实来源。"
        " / Save the candidate profile used as the factual source for job analysis and HR replies."
    ),
)
def save_profile(profile: CandidateProfileInput) -> ProfileSaveResponse:
    profile_id = save_candidate_profile(profile)
    return ProfileSaveResponse(
        success=True,
        profile_id=profile_id,
        message="candidate_profile saved",
    )


@router.get(
    "/profile",
    response_model=ProfileGetResponse,
    summary="读取候选人档案 / Read candidate profile",
    description=(
        "读取当前 candidate_profile。 / Read the current candidate profile."
    ),
)
def read_profile() -> ProfileGetResponse:
    profile = get_candidate_profile()
    if profile is None:
        return ProfileGetResponse(
            success=False,
            message="candidate_profile not found",
            data=None,
        )
    return ProfileGetResponse(
        success=True,
        message="candidate_profile found",
        data=profile,
    )
