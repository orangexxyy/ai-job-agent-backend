from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from app.schemas.application_schema import (
    ApplicationCreateRequest,
    ApplicationHrReplyConfirmRequest,
    ApplicationHrReplyConfirmResponse,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdateRequest,
)
from app.services.application_service import (
    confirm_application_hr_reply,
    create_application,
    get_application,
    list_applications,
    update_application,
)


router = APIRouter(prefix="/applications", tags=["applications"])


@router.post(
    "/{application_id}/confirm_hr_reply",
    response_model=ApplicationHrReplyConfirmResponse,
    summary="用户确认 HR 回复后更新内部状态 / Confirm HR reply and update application state",
    description=(
        "用户人工审核并手动处理 HR 回复后，记录 application 内部状态。"
        "这不代表系统自动发送 HR 消息，也不会自动投递或自动确认面试。"
        " / Record application state only after the user has reviewed and handled the HR reply manually. "
        "This endpoint does not send messages, apply to jobs, or confirm interviews automatically."
    ),
)
def confirm_application_hr_reply_record(
    application_id: int,
    request: ApplicationHrReplyConfirmRequest,
) -> ApplicationHrReplyConfirmResponse:
    try:
        data = confirm_application_hr_reply(application_id, request)
    except ValueError as exc:
        message = str(exc)
        status_code = 409 if message.startswith("terminal application status") else 422
        raise HTTPException(status_code=status_code, detail=message) from exc
    if data is None:
        raise HTTPException(status_code=404, detail="application not found")
    return ApplicationHrReplyConfirmResponse(
        success=True,
        message=(
            "HR reply already confirmed"
            if data["already_confirmed"]
            else "HR reply confirmed by user"
        ),
        data=data,
    )


@router.post(
    "",
    response_model=ApplicationResponse,
    summary="创建投递记录 / Create application record",
    description="手动创建一条 application 投递记录。 / Manually create an application record.",
)
def create_application_record(
    request: ApplicationCreateRequest,
) -> ApplicationResponse:
    try:
        data = create_application(request)
    except ValueError as exc:
        return ApplicationResponse(success=False, message=str(exc), data=None)
    return ApplicationResponse(
        success=True,
        message="application created",
        data=data,
    )


@router.get(
    "",
    response_model=ApplicationListResponse,
    summary="查询投递记录列表 / List application records",
    description="按可选条件查询 application 列表。 / List application records with optional filters.",
)
def list_application_records(
    status: Optional[str] = None,
    company_name: Optional[str] = None,
    job_title: Optional[str] = None,
    limit: int = Query(default=50, ge=1, le=100),
) -> ApplicationListResponse:
    try:
        data = list_applications(
            status=status,
            company_name=company_name,
            job_title=job_title,
            limit=limit,
        )
    except ValueError as exc:
        return ApplicationListResponse(success=False, message=str(exc), data=[])
    return ApplicationListResponse(
        success=True,
        message="applications listed",
        data=data,
    )


@router.get(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="查询单个投递记录 / Get application record",
    description="按 application_id 读取一条投递记录。 / Read one application record by application_id.",
)
def get_application_record(application_id: int) -> ApplicationResponse:
    data = get_application(application_id)
    if data is None:
        return ApplicationResponse(
            success=False,
            message="application not found",
            data=None,
        )
    return ApplicationResponse(
        success=True,
        message="application found",
        data=data,
    )


@router.patch(
    "/{application_id}",
    response_model=ApplicationResponse,
    summary="更新投递记录 / Update application record",
    description="手动更新 application 的允许字段。 / Manually update allowed application fields.",
)
def update_application_record(
    application_id: int,
    request: ApplicationUpdateRequest,
) -> ApplicationResponse:
    try:
        data = update_application(application_id, request)
    except ValueError as exc:
        return ApplicationResponse(success=False, message=str(exc), data=None)
    if data is None:
        return ApplicationResponse(
            success=False,
            message="application not found",
            data=None,
        )
    return ApplicationResponse(
        success=True,
        message="application updated",
        data=data,
    )
