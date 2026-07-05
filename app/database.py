import sqlite3
from pathlib import Path
from typing import Iterator

from app.config import settings
from app.models import (
    APPLICATION_ACTION_HISTORY_INDEX_SQL,
    APPLICATION_ACTION_HISTORY_TABLE_SQL,
    APPLICATIONS_TABLE_SQL,
    CANDIDATE_PROFILE_TABLE_SQL,
    INTERVIEW_AVAILABILITY_SLOTS_TABLE_SQL,
    PROFILE_APPLY_HISTORY_TABLE_SQL,
)


APPLICATION_OPTIONAL_COLUMNS = {
    "source_type": "TEXT",
    "jd_summary": "TEXT",
    "jd_keywords": "TEXT",
    "jd_required_skills": "TEXT",
    "jd_years_requirement": "TEXT",
    "jd_location_requirement": "TEXT",
    "jd_remote_type": "TEXT",
}


def get_database_path() -> Path:
    return settings.database_file


def get_connection() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    connection = get_connection()
    try:
        connection.execute(CANDIDATE_PROFILE_TABLE_SQL)
        connection.execute(APPLICATIONS_TABLE_SQL)
        connection.execute(INTERVIEW_AVAILABILITY_SLOTS_TABLE_SQL)
        connection.execute(APPLICATION_ACTION_HISTORY_TABLE_SQL)
        connection.execute(APPLICATION_ACTION_HISTORY_INDEX_SQL)
        connection.execute(PROFILE_APPLY_HISTORY_TABLE_SQL)
        _ensure_optional_columns(connection, "applications", APPLICATION_OPTIONAL_COLUMNS)
        connection.commit()
    finally:
        connection.close()


def _ensure_optional_columns(
    connection: sqlite3.Connection,
    table_name: str,
    columns: dict[str, str],
) -> None:
    existing_columns = {
        row["name"]
        for row in connection.execute(f"PRAGMA table_info({table_name})").fetchall()
    }
    for column_name, column_type in columns.items():
        if column_name not in existing_columns:
            connection.execute(
                f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_type}"
            )


def connection_scope() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
