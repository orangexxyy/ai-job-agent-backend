from typing import Optional

from fastapi import APIRouter, Query

from app.schemas.interview_availability_schema import (
    InterviewAvailabilitySlotCreateRequest,
    InterviewAvailabilitySlotListResponse,
    InterviewAvailabilitySlotResponse,
    InterviewAvailabilitySlotUpdateRequest,
)
from app.services.interview_availability_service import (
    create_interview_availability_slot,
    list_interview_availability_slots,
    update_interview_availability_slot,
)


router = APIRouter(
    prefix="/interview_availability_slots",
    tags=["interview_availability_slots"],
)


@router.post("", response_model=InterviewAvailabilitySlotResponse)
def create_slot(
    request: InterviewAvailabilitySlotCreateRequest,
) -> InterviewAvailabilitySlotResponse:
    try:
        data = create_interview_availability_slot(request)
    except ValueError as exc:
        return InterviewAvailabilitySlotResponse(success=False, message=str(exc), data=None)
    return InterviewAvailabilitySlotResponse(
        success=True,
        message="interview availability slot created",
        data=data,
    )


@router.get("", response_model=InterviewAvailabilitySlotListResponse)
def list_slots(
    status: Optional[str] = "available",
    limit: int = Query(default=50, ge=1, le=100),
) -> InterviewAvailabilitySlotListResponse:
    try:
        data = list_interview_availability_slots(status=status, limit=limit)
    except ValueError as exc:
        return InterviewAvailabilitySlotListResponse(success=False, message=str(exc), data=[])
    return InterviewAvailabilitySlotListResponse(
        success=True,
        message="interview availability slots listed",
        data=data,
    )


@router.patch("/{slot_id}", response_model=InterviewAvailabilitySlotResponse)
def update_slot(
    slot_id: int,
    request: InterviewAvailabilitySlotUpdateRequest,
) -> InterviewAvailabilitySlotResponse:
    try:
        data = update_interview_availability_slot(slot_id, request)
    except ValueError as exc:
        return InterviewAvailabilitySlotResponse(success=False, message=str(exc), data=None)
    if data is None:
        return InterviewAvailabilitySlotResponse(
            success=False,
            message="interview availability slot not found",
            data=None,
        )
    return InterviewAvailabilitySlotResponse(
        success=True,
        message="interview availability slot updated",
        data=data,
    )
