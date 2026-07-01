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


@router.post("", response_model=ApplicationResponse)
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


@router.get("", response_model=ApplicationListResponse)
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


@router.get("/{application_id}", response_model=ApplicationResponse)
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


@router.patch("/{application_id}", response_model=ApplicationResponse)
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
