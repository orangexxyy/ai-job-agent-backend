import sqlite3
from pathlib import Path
from typing import Iterator

from app.config import settings
from app.models import CANDIDATE_PROFILE_TABLE_SQL


def get_database_path() -> Path:
    return settings.database_file


def get_connection() -> sqlite3.Connection:
    database_path = get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    return connection


def init_database() -> None:
    with get_connection() as connection:
        connection.execute(CANDIDATE_PROFILE_TABLE_SQL)
        connection.commit()


def connection_scope() -> Iterator[sqlite3.Connection]:
    connection = get_connection()
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()
