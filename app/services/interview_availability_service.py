from datetime import datetime, timezone
from sqlite3 import Row
from typing import Any, Dict, List, Optional

from app.database import get_connection
from app.schemas.interview_availability_schema import (
    InterviewAvailabilitySlotBookRequest,
    InterviewAvailabilitySlotCreateRequest,
    InterviewAvailabilitySlotItem,
    InterviewAvailabilitySlotUpdateRequest,
    VALID_INTERVIEW_SLOT_STATUSES,
)
from app.services.action_history_service import create_application_action_history


SLOT_COLUMNS = [
    "date",
    "start_time",
    "end_time",
    "timezone",
    "status",
    "note",
    "created_at",
    "updated_at",
]


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_model(model: Any, *, exclude_unset: bool = False) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


def _validate_status(status: str) -> None:
    if status not in VALID_INTERVIEW_SLOT_STATUSES:
        allowed = ", ".join(sorted(VALID_INTERVIEW_SLOT_STATUSES))
        raise ValueError(f"invalid status '{status}'. allowed values: {allowed}")


def _row_to_slot(row: Row) -> InterviewAvailabilitySlotItem:
    data = dict(row)
    data["note"] = data.get("note") or ""
    return InterviewAvailabilitySlotItem(**data)


def create_interview_availability_slot(
    request: InterviewAvailabilitySlotCreateRequest,
) -> InterviewAvailabilitySlotItem:
    """创建一条面试可用时间段。

    主要输入：date、start_time、end_time、timezone、status 和 note。
    主要输出：创建后的 InterviewAvailabilitySlotItem。
    副作用：会写入 SQLite；不连接真实日历，不自动确认面试，不自动发送 HR 消息。
    """
    _validate_status(request.status)
    now = _now_iso()
    data = _dump_model(request)
    data["created_at"] = now
    data["updated_at"] = now
    placeholders = ", ".join([":" + column for column in SLOT_COLUMNS])

    connection = get_connection()
    try:
        duplicate = connection.execute(
            """
            SELECT * FROM interview_availability_slots
            WHERE date = ?
              AND start_time = ?
              AND end_time = ?
              AND timezone = ?
            ORDER BY id ASC
            LIMIT 1
            """,
            (request.date, request.start_time, request.end_time, request.timezone),
        ).fetchone()
        if duplicate is not None:
            raise ValueError("duplicate slot exists")
        cursor = connection.execute(
            f"""
            INSERT INTO interview_availability_slots ({", ".join(SLOT_COLUMNS)})
            VALUES ({placeholders})
            """,
            data,
        )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM interview_availability_slots WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        connection.close()

    return _row_to_slot(row)


def list_interview_availability_slots(
    status: Optional[str] = "available",
    limit: int = 50,
) -> List[InterviewAvailabilitySlotItem]:
    """查询面试可用时间段列表。

    主要输入：可选 status 和 limit；默认只返回 status=available。
    主要输出：按 date / start_time 排序的 InterviewAvailabilitySlotItem 列表。
    副作用：只读 SQLite；不连接真实日历，不自动确认面试，不自动发送 HR 消息。
    """
    filters = []
    params: Dict[str, Any] = {"limit": min(limit, 100)}
    if status and status != "all":
        _validate_status(status)
        filters.append("status = :status")
        params["status"] = status
    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""

    connection = get_connection()
    try:
        rows = connection.execute(
            f"""
            SELECT * FROM interview_availability_slots
            {where_clause}
            ORDER BY date ASC, start_time ASC, id ASC
            LIMIT :limit
            """,
            params,
        ).fetchall()
    finally:
        connection.close()

    return [_row_to_slot(row) for row in rows]


def update_interview_availability_slot(
    slot_id: int,
    request: InterviewAvailabilitySlotUpdateRequest,
) -> Optional[InterviewAvailabilitySlotItem]:
    """更新一条面试可用时间段的状态或备注。

    主要输入：slot_id，以及可选 status / note。
    主要输出：更新后的 InterviewAvailabilitySlotItem；不存在时返回 None。
    副作用：会写入 SQLite；不连接真实日历，不自动确认面试，不自动发送 HR 消息。
    """
    data = _dump_model(request, exclude_unset=True)
    data = {key: value for key, value in data.items() if key in {"status", "note"}}
    if not data:
        return get_interview_availability_slot(slot_id)
    if data.get("status") is not None:
        _validate_status(data["status"])
    data["updated_at"] = _now_iso()
    data["slot_id"] = slot_id
    assignments = ", ".join([f"{field} = :{field}" for field in data if field != "slot_id"])

    connection = get_connection()
    try:
        cursor = connection.execute(
            f"""
            UPDATE interview_availability_slots
            SET {assignments}
            WHERE id = :slot_id
            """,
            data,
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return None
        connection.commit()
        row = connection.execute(
            "SELECT * FROM interview_availability_slots WHERE id = ?",
            (slot_id,),
        ).fetchone()
    finally:
        connection.close()

    return _row_to_slot(row)


def book_interview_availability_slot(
    slot_id: int,
    request: InterviewAvailabilitySlotBookRequest,
) -> Optional[InterviewAvailabilitySlotItem]:
    """将用户确认占用的面试时间段标记为 booked。

    主要输入：slot_id，以及可选 application_id / note。
    主要输出：更新后的 InterviewAvailabilitySlotItem；不存在时返回 None。
    副作用：会写入 SQLite；不更新 application，不发送 HR 消息，不连接外部日历。
    """
    slot = get_interview_availability_slot(slot_id)
    if slot is None:
        return None
    if slot.status not in {"available", "held"}:
        raise ValueError("slot cannot be booked from current status")

    note = request.note.strip() if request.note else slot.note
    update = InterviewAvailabilitySlotUpdateRequest(status="booked", note=note)
    updated = update_interview_availability_slot(slot_id, update)
    if updated is not None:
        create_application_action_history(
            application_id=request.application_id,
            action_type="interview_slot_booked",
            action_source="user",
            before_status=slot.status,
            after_status=updated.status,
            before_next_action=None,
            after_next_action=None,
            user_confirmed=True,
            external_action_performed=False,
            risk_level="medium",
            summary="Interview availability slot booked",
            detail_json={
                "slot_id": updated.id,
                "date": updated.date,
                "start_time": updated.start_time,
                "end_time": updated.end_time,
                "timezone": updated.timezone,
                "note_preview": " ".join((updated.note or "").split())[:120],
            },
        )
    return updated


def get_interview_availability_slot(
    slot_id: int,
) -> Optional[InterviewAvailabilitySlotItem]:
    """按 id 读取一条面试可用时间段。

    主要输入：slot_id。
    主要输出：找到时返回 InterviewAvailabilitySlotItem，否则返回 None。
    副作用：只读 SQLite；不连接真实日历，不自动确认面试。
    """
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM interview_availability_slots WHERE id = ?",
            (slot_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    return _row_to_slot(row)
