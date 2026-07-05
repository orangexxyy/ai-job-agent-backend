import json
from datetime import datetime, timezone
from sqlite3 import Row
from typing import Any, Dict, List, Optional

from app.database import get_connection
from app.schemas.profile_apply_history_schema import ProfileApplyHistoryItem


DETAIL_FIELDS = {
    "target_roles_count",
    "available_projects_count",
    "truth_boundaries_count",
    "resume_text_length",
    "project_context_length",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _row_to_history(row: Row) -> ProfileApplyHistoryItem:
    data = dict(row)
    raw_detail = data.get("detail_json")
    try:
        data["detail_json"] = json.loads(raw_detail) if raw_detail else {}
    except (TypeError, json.JSONDecodeError):
        data["detail_json"] = {}
    data["profile_verified"] = bool(data.get("profile_verified"))
    data["user_confirmed"] = bool(data.get("user_confirmed"))
    data["external_action_performed"] = bool(
        data.get("external_action_performed")
    )
    return ProfileApplyHistoryItem(**data)


def _validate_detail(detail_json: Optional[Dict[str, Any]]) -> Dict[str, int]:
    detail = detail_json or {}
    unsupported = sorted(set(detail) - DETAIL_FIELDS)
    if unsupported:
        raise ValueError(
            "profile apply history detail contains unsupported fields: "
            + ", ".join(unsupported)
        )
    normalized: Dict[str, int] = {}
    for field in DETAIL_FIELDS:
        value = detail.get(field, 0)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise ValueError(f"profile apply history detail field must be a non-negative integer: {field}")
        normalized[field] = value
    return normalized


def create_profile_apply_history(
    *,
    draft_path: str,
    backup_path: Optional[str],
    profile_verified: bool,
    user_confirmed: bool,
    external_action_performed: bool,
    detail_json: Optional[Dict[str, Any]] = None,
) -> ProfileApplyHistoryItem:
    """记录一次用户确认且验证成功的 candidate_profile 草稿应用。

    主要输入为 draft / backup 路径、确认与验证标记及白名单计数摘要，输出新建记录。
    会写入 SQLite；不保存完整简历正文，不调用 LLM，也不执行任何外部动作。
    """
    if external_action_performed:
        raise ValueError("external_action_performed must remain false")
    if not user_confirmed or not profile_verified:
        raise ValueError("profile apply history requires confirmed and verified apply")
    detail = _validate_detail(detail_json)
    data = {
        "draft_path": draft_path,
        "backup_path": backup_path,
        "profile_verified": 1,
        "user_confirmed": 1,
        "external_action_performed": 0,
        "detail_json": json.dumps(detail, ensure_ascii=False, sort_keys=True),
        "created_at": _now_iso(),
    }
    connection = get_connection()
    try:
        cursor = connection.execute(
            """
            INSERT INTO profile_apply_history (
                draft_path,
                backup_path,
                profile_verified,
                user_confirmed,
                external_action_performed,
                detail_json,
                created_at
            ) VALUES (
                :draft_path,
                :backup_path,
                :profile_verified,
                :user_confirmed,
                :external_action_performed,
                :detail_json,
                :created_at
            )
            """,
            data,
        )
        connection.commit()
        row = connection.execute(
            "SELECT * FROM profile_apply_history WHERE id = ?",
            (cursor.lastrowid,),
        ).fetchone()
    finally:
        connection.close()
    return _row_to_history(row)


def list_profile_apply_history(limit: int = 50) -> List[ProfileApplyHistoryItem]:
    """查询最近的 profile apply 简单留痕。

    主要输入为最大 100 的 limit，输出按 id 倒序排列的记录。
    只读 SQLite；不读取完整简历正文，不修改 profile，也不执行外部动作。
    """
    safe_limit = max(1, min(limit, 100))
    connection = get_connection()
    try:
        rows = connection.execute(
            """
            SELECT * FROM profile_apply_history
            ORDER BY id DESC
            LIMIT ?
            """,
            (safe_limit,),
        ).fetchall()
    finally:
        connection.close()
    return [_row_to_history(row) for row in rows]
