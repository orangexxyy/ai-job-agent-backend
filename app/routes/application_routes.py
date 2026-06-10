from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.application_schema import (
    ApplicationCreateRequest,
    ApplicationListResponse,
    ApplicationResponse,
    ApplicationUpdateRequest,
)
from app.services.application_service import (
    create_application,
    get_application,
    list_applications,
    update_application,
)


router = APIRouter(prefix="/applications", tags=["applications"])


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
