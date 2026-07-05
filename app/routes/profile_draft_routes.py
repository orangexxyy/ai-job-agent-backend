from fastapi import APIRouter, HTTPException, Request

from app.schemas.profile_draft_schema import (
    ProfileDraftApplyData,
    ProfileDraftApplyRequest,
    ProfileDraftApplyResponse,
    ProfileDraftReviewResponse,
)
from app.services.profile_draft_service import (
    apply_profile_draft,
    get_profile_draft_review,
)


router = APIRouter(prefix="/profile_draft", tags=["profile_draft"])
LOCAL_CLIENT_HOSTS = {"127.0.0.1", "::1", "localhost"}


def _require_local_request(request: Request) -> None:
    client_host = request.client.host if request.client else ""
    if client_host not in LOCAL_CLIENT_HOSTS:
        raise HTTPException(status_code=403, detail="profile draft API is local-only")
    if request.query_params:
        raise HTTPException(
            status_code=422,
            detail="profile draft API does not accept query parameters or file paths",
        )


@router.get(
    "/review",
    response_model=ProfileDraftReviewResponse,
    summary="审核本地 Profile Draft / Review local profile draft",
    description=(
        "读取并校验默认私有 draft，只返回结构化字段、文本预览和长度；"
        "不返回完整简历正文，不写数据库。"
    ),
)
def review_profile_draft(request: Request) -> ProfileDraftReviewResponse:
    _require_local_request(request)
    try:
        data = get_profile_draft_review()
    except OSError as exc:
        raise HTTPException(status_code=500, detail="profile draft could not be read") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="profile draft is invalid") from exc
    return ProfileDraftReviewResponse(
        success=True,
        message=(
            "profile draft review loaded"
            if data.draft_exists
            else "profile draft does not exist"
        ),
        data=data,
    )


@router.post(
    "/apply",
    response_model=ProfileDraftApplyResponse,
    summary="确认应用本地 Profile Draft / Apply reviewed local profile draft",
    description=(
        "仅接受 confirmation_text=YES。后端重新读取默认 draft，备份旧 profile，"
        "保存并验证后写最小 history；不执行任何外部动作。"
    ),
)
def apply_reviewed_profile_draft(
    request_context: Request,
    request: ProfileDraftApplyRequest,
) -> ProfileDraftApplyResponse:
    _require_local_request(request_context)
    try:
        outcome = apply_profile_draft(confirmation_text=request.confirmation_text)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail="profile draft does not exist") from exc
    except OSError as exc:
        raise HTTPException(status_code=500, detail="profile draft apply failed") from exc
    except ValueError as exc:
        raise HTTPException(status_code=422, detail="confirmation or profile draft is invalid") from exc
    data = ProfileDraftApplyData(
        applied=outcome.applied,
        profile_id=outcome.profile_id,
        backup_created=outcome.backup_created,
        profile_verified=outcome.profile_verified,
        profile_apply_history_id=outcome.profile_apply_history_id,
        external_action_performed=False,
    )
    return ProfileDraftApplyResponse(
        success=outcome.applied,
        message=(
            "profile draft applied and verified"
            if outcome.applied
            else "profile draft verification failed"
        ),
        data=data,
    )
