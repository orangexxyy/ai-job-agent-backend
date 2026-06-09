from fastapi import APIRouter

from app.schemas.profile_schema import (
    CandidateProfileInput,
    ProfileGetResponse,
    ProfileSaveResponse,
)
from app.services.profile_service import get_candidate_profile, save_candidate_profile


router = APIRouter()


@router.post("/profile", response_model=ProfileSaveResponse)
def save_profile(profile: CandidateProfileInput) -> ProfileSaveResponse:
    profile_id = save_candidate_profile(profile)
    return ProfileSaveResponse(
        success=True,
        profile_id=profile_id,
        message="candidate_profile saved",
    )


@router.get("/profile", response_model=ProfileGetResponse)
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
