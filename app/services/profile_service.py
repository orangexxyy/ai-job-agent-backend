import json
from datetime import datetime, timezone
from sqlite3 import Row
from typing import Any, Dict, Optional

from app.database import get_connection
from app.schemas.profile_schema import CandidateProfile, CandidateProfileInput


JSON_LIST_FIELDS = {
    "preferred_cities",
    "acceptable_cities",
    "target_roles",
    "available_projects",
    "truth_boundaries",
}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _serialize_profile(profile: CandidateProfileInput) -> Dict[str, Any]:
    data = (
        profile.model_dump()
        if hasattr(profile, "model_dump")
        else profile.dict()
    )
    for field in JSON_LIST_FIELDS:
        data[field] = json.dumps(data[field], ensure_ascii=False)
    return data


def _row_to_profile(row: Row) -> CandidateProfile:
    data = dict(row)
    for field in JSON_LIST_FIELDS:
        value = data.get(field)
        data[field] = json.loads(value) if value else []
    return CandidateProfile(**data)


def save_candidate_profile(profile: CandidateProfileInput) -> int:
    data = _serialize_profile(profile)
    now = _now_iso()
    columns = [
        "id",
        "expected_salary_min",
        "expected_salary_max",
        "minimum_salary",
        "salary_note",
        "availability_note",
        "preferred_cities",
        "acceptable_cities",
        "relocation_policy",
        "outsourcing_policy",
        "onsite_policy",
        "remote_policy",
        "overtime_policy",
        "business_trip_policy",
        "target_roles",
        "available_projects",
        "truth_boundaries",
        "resume_text",
        "project_context",
        "created_at",
        "updated_at",
    ]
    values = {
        **data,
        "id": 1,
        "created_at": now,
        "updated_at": now,
    }
    placeholders = ", ".join([":" + column for column in columns])
    update_clause = ", ".join(
        [
            f"{column}=excluded.{column}"
            for column in columns
            if column not in {"id", "created_at"}
        ]
    )

    connection = get_connection()
    try:
        connection.execute(
            f"""
            INSERT INTO candidate_profile ({", ".join(columns)})
            VALUES ({placeholders})
            ON CONFLICT(id) DO UPDATE SET {update_clause}
            """,
            values,
        )
        connection.commit()
    finally:
        connection.close()

    return 1


def get_candidate_profile() -> Optional[CandidateProfile]:
    connection = get_connection()
    try:
        row = connection.execute(
            "SELECT * FROM candidate_profile WHERE id = 1"
        ).fetchone()
    finally:
        connection.close()
    if row is None:
        return None
    return _row_to_profile(row)
