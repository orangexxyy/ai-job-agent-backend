import json
from datetime import datetime, timezone
from sqlite3 import Row
from typing import Any, Dict, List, Optional

from app.database import get_connection
from app.schemas.application_schema import (
    ApplicationCreateRequest,
    ApplicationItem,
    ApplicationUpdateRequest,
    VALID_APPLICATION_STATUSES,
)


APPLICATION_COLUMNS = [
    "company_name",
    "job_title",
    "job_source",
    "job_url",
    "jd_text",
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


def _row_to_application(row: Row) -> ApplicationItem:
    data = dict(row)
    value = data.get("risk_flags")
    data["risk_flags"] = json.loads(value) if value else []
    return ApplicationItem(**data)


def create_application(request: ApplicationCreateRequest) -> ApplicationItem:
    """创建一条手动投递记录。

    主要输入：包含公司、岗位、JD、状态和备注的 ApplicationCreateRequest。
    主要输出：创建后的 ApplicationItem。
    副作用：会写入 SQLite；不自动投递，不自动发送 HR 消息，不调用 LLM。
    """
    _validate_status(request.status)
    now = _now_iso()
    data = _serialize_risk_flags(_dump_model(request))
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

    return _row_to_application(row)


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

    data = _serialize_risk_flags(data)
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
