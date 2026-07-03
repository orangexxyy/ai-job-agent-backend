import json
from datetime import datetime, timezone
from sqlite3 import Row
from typing import Any, Dict, List, Optional

from app.database import get_connection
from app.schemas.action_history_schema import ApplicationActionHistoryItem


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_action_history(row: Row) -> ApplicationActionHistoryItem:
    data = dict(row)
    raw_detail = data.get("detail_json")
    try:
        data["detail_json"] = json.loads(raw_detail) if raw_detail else {}
    except (TypeError, json.JSONDecodeError):
        data["detail_json"] = {}
    data["user_confirmed"] = bool(data.get("user_confirmed"))
    data["external_action_performed"] = bool(
        data.get("external_action_performed")
    )
    return ApplicationActionHistoryItem(**data)


def create_application_action_history(
    *,
    application_id: Optional[int],
    action_type: str,
    action_source: str,
    before_status: Optional[str],
    after_status: Optional[str],
    before_next_action: Optional[str],
    after_next_action: Optional[str],
    user_confirmed: bool,
    external_action_performed: bool,
    risk_level: Optional[str],
    summary: str,
    detail_json: Optional[Dict[str, Any]] = None,
) -> ApplicationActionHistoryItem:
    """写入一条 application 关键动作历史。

    主要输入：动作类型、来源、状态前后值、用户确认标记、风险级别和精简详情。
    主要输出：创建后的 ApplicationActionHistoryItem。
    副作用：会写入 SQLite；只记录系统内部动作，不发送消息、不投递、不确认面试。
    """
    if external_action_performed:
        raise ValueError("external_action_performed must remain false")
    data = {
        "application_id": application_id,
        "action_type": action_type,
        "action_source": action_source,
        "before_status": before_status,
        "after_status": after_status,
        "before_next_action": before_next_action,
        "after_next_action": after_next_action,
        "user_confirmed": int(user_confirmed),
        "external_action_performed": 0,
        "risk_level": risk_level,
        "summary": summary,
        "detail_json": json.dumps(detail_json or {}, ensure_ascii=False),
        "created_at": _now_iso(),
    }
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO application_action_history (
                application_id,
                action_type,
                action_source,
                before_status,
                after_status,
                before_next_action,
                after_next_action,
                user_confirmed,
                external_action_performed,
                risk_level,
                summary,
                detail_json,
                created_at
            ) VALUES (
                :application_id,
                :action_type,
                :action_source,
                :before_status,
                :after_status,
                :before_next_action,
                :after_next_action,
                :user_confirmed,
                :external_action_performed,
                :risk_level,
                :summary,
                :detail_json,
                :created_at
            )
            """,
            data,
        )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM application_action_history WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        connection.close()
    return _row_to_action_history(row)


def list_application_action_history(
    application_id: int,
    limit: int = 50,
) -> List[ApplicationActionHistoryItem]:
    """按 application_id 查询最近的关键动作历史。

    主要输入：application_id 和最大 100 的 limit。
    主要输出：按 id 倒序排列的 ApplicationActionHistoryItem 列表。
    副作用：只读 SQLite；不修改 application，不执行任何外部动作。
    """
    safe_limit = max(1, min(limit, 100))
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT *
            FROM application_action_history
            WHERE application_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (application_id, safe_limit),
        ).fetchall()
    finally:
        connection.close()
    return [_row_to_action_history(row) for row in rows]
