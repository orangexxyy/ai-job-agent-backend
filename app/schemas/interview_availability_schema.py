from typing import List, Optional

from pydantic import BaseModel


VALID_INTERVIEW_SLOT_STATUSES = {"available", "held", "booked", "expired"}


class InterviewAvailabilitySlotCreateRequest(BaseModel):
    date: str
    start_time: str
    end_time: str
    timezone: str = "Asia/Shanghai"
    status: str = "available"
    note: str = ""


class InterviewAvailabilitySlotUpdateRequest(BaseModel):
    status: Optional[str] = None
    note: Optional[str] = None


class InterviewAvailabilitySlotBookRequest(BaseModel):
    application_id: Optional[int] = None
    note: str = ""


class InterviewAvailabilitySlotItem(BaseModel):
    id: int
    date: str
    start_time: str
    end_time: str
    timezone: str
    status: str
    note: str = ""
    created_at: str
    updated_at: str


class InterviewAvailabilitySlotResponse(BaseModel):
    success: bool
    message: str
    data: Optional[InterviewAvailabilitySlotItem] = None


class InterviewAvailabilitySlotListResponse(BaseModel):
    success: bool
    message: str
    data: List[InterviewAvailabilitySlotItem]
