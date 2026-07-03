import hashlib
import json
from datetime import datetime, timezone
from sqlite3 import Row
from typing import Any, Dict, List, Optional

from app.database import get_connection
from app.schemas.application_schema import (
    ApplicationCreateRequest,
    ApplicationHrReplyConfirmRequest,
    ApplicationItem,
    ApplicationUpdateRequest,
    VALID_APPLICATION_STATUSES,
)
from app.services.jd_parser_service import normalize_source, parse_jd
from app.services.action_history_service import create_application_action_history


APPLICATION_COLUMNS = [
    "company_name",
    "job_title",
    "job_source",
    "job_url",
    "jd_text",
    "source_type",
    "jd_summary",
    "jd_keywords",
    "jd_required_skills",
    "jd_years_requirement",
    "jd_location_requirement",
    "jd_remote_type",
    "status",
    "match_score",
    "hr_contact_name",
    "hr_contact_channel",
    "last_hr_message",
    "next_action",
    "next_action_due_date",
    "notes",
    "risk_flags",
    "created_at",
    "updated_at",
]


UPDATABLE_FIELDS = {
    "company_name",
    "job_title",
    "job_source",
    "job_url",
    "jd_text",
    "source_type",
    "jd_summary",
    "jd_keywords",
    "jd_required_skills",
    "jd_years_requirement",
    "jd_location_requirement",
    "jd_remote_type",
    "status",
    "match_score",
    "hr_contact_name",
    "hr_contact_channel",
    "last_hr_message",
    "next_action",
    "next_action_due_date",
    "notes",
    "risk_flags",
}


REQUIRED_TEXT_FIELDS = {"company_name", "job_title", "status"}
TERMINAL_APPLICATION_STATUSES = {"offer", "rejected", "closed"}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _dump_model(model: Any, *, exclude_unset: bool = False) -> Dict[str, Any]:
    if hasattr(model, "model_dump"):
        return model.model_dump(exclude_unset=exclude_unset)
    return model.dict(exclude_unset=exclude_unset)


def _validate_status(status: str) -> None:
    if status not in VALID_APPLICATION_STATUSES:
        allowed = ", ".join(sorted(VALID_APPLICATION_STATUSES))
        raise ValueError(f"invalid status '{status}'. allowed values: {allowed}")


def _serialize_risk_flags(data: Dict[str, Any]) -> Dict[str, Any]:
    if "risk_flags" in data:
        data["risk_flags"] = json.dumps(data["risk_flags"] or [], ensure_ascii=False)
    return data


def _serialize_json_list_fields(data: Dict[str, Any]) -> Dict[str, Any]:
    for field in ("jd_keywords", "jd_required_skills"):
        if field in data:
            data[field] = json.dumps(data[field] or [], ensure_ascii=False)
    return data


def _row_to_application(row: Row) -> ApplicationItem:
    data = dict(row)
    value = data.get("risk_flags")
    data["risk_flags"] = json.loads(value) if value else []
    data["source"] = data.get("job_source") or ""
    for field in ("jd_keywords", "jd_required_skills"):
        value = data.get(field)
        data[field] = json.loads(value) if value else []
    for field in (
        "source_type",
        "jd_summary",
        "jd_years_requirement",
        "jd_location_requirement",
        "jd_remote_type",
    ):
        data[field] = data.get(field) or ("unknown" if field == "jd_remote_type" else "")
    return ApplicationItem(**data)


def _source_from_data(data: Dict[str, Any]) -> str:
    source = data.pop("source", None)
    if source and not data.get("job_source"):
        data["job_source"] = source
    return data.get("job_source") or source or ""


def _apply_jd_parse_fields(data: Dict[str, Any], *, source: str, jd_text: str) -> None:
    parsed = parse_jd(jd_text or "", source)
    data.update(parsed)


def create_application(request: ApplicationCreateRequest) -> ApplicationItem:
    """创建一条手动投递记录。

    主要输入：包含公司、岗位、JD、状态和备注的 ApplicationCreateRequest。
    主要输出：创建后的 ApplicationItem。
    副作用：会写入 SQLite；不自动投递，不自动发送 HR 消息，不调用 LLM。
    """
    _validate_status(request.status)
    now = _now_iso()
    data = _dump_model(request)
    source = _source_from_data(data)
    _apply_jd_parse_fields(data, source=source, jd_text=data.get("jd_text") or "")
    data = _serialize_json_list_fields(_serialize_risk_flags(data))
    data["created_at"] = now
    data["updated_at"] = now

    placeholders = ", ".join([":" + column for column in APPLICATION_COLUMNS])
    connection = get_connection()
    try:
        cursor = connection.execute(
            f"""
            INSERT INTO applications ({", ".join(APPLICATION_COLUMNS)})
            VALUES ({placeholders})
            """,
            data,
        )
        connection.commit()
        application_id = cursor.lastrowid
        row = connection.execute(
            "SELECT * FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()
    finally:
        connection.close()

    application = _row_to_application(row)
    create_application_action_history(
        application_id=application.id,
        action_type="application_created",
        action_source="user",
        before_status=None,
        after_status=application.status,
        before_next_action=None,
        after_next_action=application.next_action,
        user_confirmed=True,
        external_action_performed=False,
        risk_level="low",
        summary="Application created",
        detail_json={
            "company_name": application.company_name,
            "job_title": application.job_title,
            "source_type": application.source_type,
            "jd_keywords_preview": application.jd_keywords[:10],
        },
    )
    return application


def list_applications(
    status: Optional[str] = None,
    company_name: Optional[str] = None,
    job_title: Optional[str] = None,
    limit: int = 50,
) -> List[ApplicationItem]:
    """查询投递记录列表。

    主要输入：可选的 status、company_name、job_title 和 limit 过滤条件。
    主要输出：按更新时间排序的 ApplicationItem 列表。
    副作用：只读数据库；不修改 application，不调用 LLM。
    """
    if status is not None:
        _validate_status(status)

    filters = []
    params: Dict[str, Any] = {"limit": min(limit, 100)}
    if status:
        filters.append("status = :status")
        params["status"] = status
    if company_name:
        filters.append("company_name LIKE :company_name")
        params["company_name"] = f"%{company_name}%"
    if job_title:
        filters.append("job_title LIKE :job_title")
        params["job_title"] = f"%{job_title}%"

    where_clause = f"WHERE {' AND '.join(filters)}" if filters else ""
    connection = get_connection()
    try:
        rows = connection.execute(
            f"""
            SELECT * FROM applications
            {where_clause}
            ORDER BY updated_at DESC, id DESC
            LIMIT :limit
            """,
            params,
        ).fetchall()
    finally:
        connection.close()

    return [_row_to_application(row) for row in rows]


def get_application(application_id: int) -> Optional[ApplicationItem]:
    """按 id 读取一条投递记录。

    主要输入：application_id。
    主要输出：找到时返回 ApplicationItem，否则返回 None。
    副作用：只读数据库；不修改 application，不调用 LLM。
    """
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    return _row_to_application(row)


def update_application(
    application_id: int,
    request: ApplicationUpdateRequest,
) -> Optional[ApplicationItem]:
    """局部更新一条投递记录。

    主要输入：application_id 和 ApplicationUpdateRequest 中允许更新的字段。
    主要输出：更新后的 ApplicationItem；空更新返回当前记录；不存在返回 None。
    副作用：会更新 application 并写入 SQLite；不自动投递，不自动发送 HR 消息，不调用 LLM。
    """
    data = _dump_model(request, exclude_unset=True)
    source_provided = "source" in data or "job_source" in data
    jd_text_provided = "jd_text" in data
    source_input = data.pop("source", None)
    if source_input and data.get("job_source") is None:
        data["job_source"] = source_input
    data = {key: value for key, value in data.items() if key in UPDATABLE_FIELDS}
    if not data:
        return get_application(application_id)
    null_required_fields = [
        field for field in REQUIRED_TEXT_FIELDS if field in data and data[field] is None
    ]
    if null_required_fields:
        fields = ", ".join(sorted(null_required_fields))
        raise ValueError(f"{fields} cannot be null")
    if "status" in data and data["status"] is not None:
        _validate_status(data["status"])

    if source_provided or jd_text_provided:
        current = get_application(application_id)
        if current is None:
            return None
        source = data.get("job_source")
        if source is None:
            source = current.job_source or source_input or ""
        jd_text = data.get("jd_text")
        if jd_text is None:
            jd_text = current.jd_text or ""
        if source_provided:
            data["source_type"] = normalize_source(source)
        if jd_text_provided:
            _apply_jd_parse_fields(data, source=source, jd_text=jd_text)

    data = _serialize_json_list_fields(_serialize_risk_flags(data))
    data["updated_at"] = _now_iso()
    data["application_id"] = application_id

    assignments = ", ".join(
        [f"{field} = :{field}" for field in data if field != "application_id"]
    )
    connection = get_connection()
    try:
        cursor = connection.execute(
            f"""
            UPDATE applications
            SET {assignments}
            WHERE id = :application_id
            """,
            data,
        )
        if cursor.rowcount == 0:
            connection.rollback()
            return None
        connection.commit()
        row = connection.execute(
            "SELECT * FROM applications WHERE id = ?",
            (application_id,),
        ).fetchone()
    finally:
        connection.close()

    return _row_to_application(row)


def confirm_application_hr_reply(
    application_id: int,
    request: ApplicationHrReplyConfirmRequest,
) -> Optional[Dict[str, Any]]:
    """在用户确认已处理 HR 回复后，安全更新 application 内部状态。

    主要输入：application_id、用户确认采用的 draft_text、可选 HR 原消息、下一步动作和备注。
    主要输出：更新后的 application、重复确认标记和 Human-in-the-loop 安全 debug。
    副作用：会写入 SQLite；不会自动发送 HR 消息、自动投递或自动确认面试。
    """
    application = get_application(application_id)
    if application is None:
        return None

    draft_text = request.draft_text.strip()
    if not draft_text:
        raise ValueError("draft_text cannot be empty")
    next_action = request.next_action.strip()
    if not next_action:
        raise ValueError("next_action cannot be empty")
    if application.status in TERMINAL_APPLICATION_STATUSES:
        raise ValueError(
            f"terminal application status '{application.status}' cannot be overwritten"
        )

    existing_notes = application.notes or ""
    draft_marker = f"draft_text: {draft_text}"
    already_confirmed = (
        application.status == "hr_replied"
        and application.next_action == next_action
        and draft_marker in existing_notes
    )
    if already_confirmed:
        return _build_hr_reply_confirmation_result(
            application=application,
            sent_channel=request.sent_channel,
            already_confirmed=True,
            database_write_performed=False,
        )

    record_lines = [
        "[HR_REPLY_CONFIRMED]",
        f"confirmed_at: {_now_iso()}",
        f"sent_channel: {request.sent_channel}",
        draft_marker,
    ]
    hr_message = (request.hr_message or "").strip()
    note = request.note.strip()
    if hr_message:
        record_lines.append(f"hr_message: {hr_message}")
    if note:
        record_lines.append(f"note: {note}")
    confirmation_record = "\n".join(record_lines)
    notes = f"{existing_notes.rstrip()}\n\n{confirmation_record}".strip()

    update_fields: Dict[str, Any] = {
        "status": "hr_replied",
        "next_action": next_action,
        "notes": notes,
    }
    if hr_message:
        update_fields["last_hr_message"] = hr_message

    updated = update_application(
        application_id,
        ApplicationUpdateRequest(**update_fields),
    )
    if updated is None:
        return None
    create_application_action_history(
        application_id=updated.id,
        action_type="hr_reply_confirmed",
        action_source="user",
        before_status=application.status,
        after_status=updated.status,
        before_next_action=application.next_action,
        after_next_action=updated.next_action,
        user_confirmed=True,
        external_action_performed=False,
        risk_level="medium",
        summary="User confirmed HR reply was handled manually",
        detail_json={
            "sent_channel": request.sent_channel,
            "draft_text_preview": _text_preview(draft_text),
            "draft_text_hash": hashlib.sha256(draft_text.encode("utf-8")).hexdigest(),
            "hr_message_preview": _text_preview(hr_message),
            "note_preview": _text_preview(note),
        },
    )
    return _build_hr_reply_confirmation_result(
        application=updated,
        sent_channel=request.sent_channel,
        already_confirmed=False,
        database_write_performed=True,
    )


def _build_hr_reply_confirmation_result(
    *,
    application: ApplicationItem,
    sent_channel: str,
    already_confirmed: bool,
    database_write_performed: bool,
) -> Dict[str, Any]:
    return {
        "application_id": application.id,
        "status": application.status,
        "next_action": application.next_action,
        "sent_channel": sent_channel,
        "confirmation_recorded": True,
        "already_confirmed": already_confirmed,
        "application": application,
        "debug": {
            "auto_send_message": False,
            "auto_apply": False,
            "auto_confirm_interview": False,
            "database_write_intended": True,
            "database_write_performed": database_write_performed,
            "confirmed_by_user": True,
        },
    }


def _text_preview(value: str, limit: int = 120) -> str:
    normalized = " ".join((value or "").split())
    return normalized[:limit]
