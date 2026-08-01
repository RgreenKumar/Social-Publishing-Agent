import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

import pandas as pd


# =========================================================
# Database configuration
# =========================================================

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "post_history.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)


# Columns added after the original database was created.
# init_db() will automatically add any missing columns.
MIGRATION_COLUMNS = {
    "tone": "TEXT",
    "user_prompt": "TEXT",
    "company_url": "TEXT",
    "research_summary": "TEXT",
    "source_urls": "TEXT",
    "media_name": "TEXT",
    "media_type": "TEXT",
    "media_notes": "TEXT",
    "published_url": "TEXT",
    "error_message": "TEXT",
    "updated_at": "TEXT",
}


# =========================================================
# Connection handling
# =========================================================

@contextmanager
def get_connection():
    """
    Creates a safe SQLite connection.

    Automatically commits successful operations and rolls
    back failed operations.
    """

    conn = sqlite3.connect(
        str(DB_PATH),
        timeout=30,
        check_same_thread=False,
    )

    conn.row_factory = sqlite3.Row

    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


# =========================================================
# Helpers
# =========================================================

def current_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def serialize_sources(source_urls: Any) -> Optional[str]:
    """
    Converts a list of source dictionaries or URLs into JSON.
    Existing strings are stored without modification.
    """

    if source_urls is None:
        return None

    if isinstance(source_urls, str):
        return source_urls

    return json.dumps(
        source_urls,
        ensure_ascii=False,
    )


def deserialize_sources(source_urls: Optional[str]) -> list:
    """
    Converts saved source JSON back into a Python list.
    """

    if not source_urls:
        return []

    try:
        result = json.loads(source_urls)

        if isinstance(result, list):
            return result

        return [result]

    except (json.JSONDecodeError, TypeError):
        return [source_urls]


# =========================================================
# Database initialization and migration
# =========================================================

def init_db():
    """
    Creates the posts table and upgrades older databases.
    """

    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                update_id INTEGER,
                company TEXT,
                title TEXT,
                platform TEXT,
                draft TEXT,
                status TEXT,
                scheduled_time TEXT,
                recommended_time TEXT,
                publish_mode TEXT,
                tone TEXT,
                user_prompt TEXT,
                company_url TEXT,
                research_summary TEXT,
                source_urls TEXT,
                media_name TEXT,
                media_type TEXT,
                media_notes TEXT,
                published_url TEXT,
                error_message TEXT,
                updated_at TEXT
            )
            """
        )

        existing_columns = {
            row["name"]
            for row in conn.execute(
                "PRAGMA table_info(posts)"
            ).fetchall()
        }

        for column_name, column_definition in MIGRATION_COLUMNS.items():
            if column_name not in existing_columns:
                conn.execute(
                    f"""
                    ALTER TABLE posts
                    ADD COLUMN "{column_name}" {column_definition}
                    """
                )

        # Add updated_at to older saved records.
        conn.execute(
            """
            UPDATE posts
            SET updated_at = COALESCE(updated_at, timestamp)
            WHERE updated_at IS NULL
            """
        )


# =========================================================
# Save post
# =========================================================

def save_post(
    update_id,
    company,
    title,
    platform,
    draft,
    status="draft",
    scheduled_time=None,
    recommended_time=None,
    publish_mode="mock",
    *,
    tone=None,
    user_prompt=None,
    company_url=None,
    research_summary=None,
    source_urls=None,
    media_name=None,
    media_type=None,
    media_notes=None,
    published_url=None,
    error_message=None,
):
    """
    Saves a generated post and returns its database ID.

    New arguments are keyword-only, so existing app.py calls
    will continue to work.
    """

    now = current_timestamp()

    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO posts (
                timestamp,
                update_id,
                company,
                title,
                platform,
                draft,
                status,
                scheduled_time,
                recommended_time,
                publish_mode,
                tone,
                user_prompt,
                company_url,
                research_summary,
                source_urls,
                media_name,
                media_type,
                media_notes,
                published_url,
                error_message,
                updated_at
            )
            VALUES (
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
            )
            """,
            (
                now,
                update_id,
                company,
                title,
                platform,
                draft,
                status,
                scheduled_time,
                recommended_time,
                publish_mode,
                tone,
                user_prompt,
                company_url,
                research_summary,
                serialize_sources(source_urls),
                media_name,
                media_type,
                media_notes,
                published_url,
                error_message,
                now,
            ),
        )

        return cursor.lastrowid


# =========================================================
# Load history
# =========================================================

def load_posts(limit: Optional[int] = None) -> pd.DataFrame:
    """
    Returns post history as a Pandas DataFrame.
    """

    query = """
        SELECT *
        FROM posts
        ORDER BY id DESC
    """

    parameters = None

    if limit is not None:
        query += " LIMIT ?"
        parameters = (int(limit),)

    with get_connection() as conn:
        return pd.read_sql_query(
            query,
            conn,
            params=parameters,
        )


# Keeps compatibility with your old function name.
def load_post(limit: Optional[int] = None) -> pd.DataFrame:
    return load_posts(limit=limit)


# =========================================================
# Get one post
# =========================================================

def get_post(post_id: int) -> Optional[dict]:
    with get_connection() as conn:
        row = conn.execute(
            """
            SELECT *
            FROM posts
            WHERE id = ?
            """,
            (post_id,),
        ).fetchone()

    return dict(row) if row else None


# =========================================================
# Update draft
# =========================================================

def update_draft(post_id: int, new_draft: str) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE posts
            SET
                draft = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                new_draft,
                current_timestamp(),
                post_id,
            ),
        )

        return cursor.rowcount > 0


# =========================================================
# Update publishing status
# =========================================================

def update_post_status(
    post_id: int,
    status: str,
    published_url: Optional[str] = None,
    error_message: Optional[str] = None,
    publish_mode: Optional[str] = None,
) -> bool:
    """
    Updates post state after approval or publishing.

    Example statuses:
    - draft
    - approved
    - publishing
    - published
    - failed
    """

    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE posts
            SET
                status = ?,
                published_url = COALESCE(?, published_url),
                error_message = ?,
                publish_mode = COALESCE(?, publish_mode),
                updated_at = ?
            WHERE id = ?
            """,
            (
                status,
                published_url,
                error_message,
                publish_mode,
                current_timestamp(),
                post_id,
            ),
        )

        return cursor.rowcount > 0


# =========================================================
# Update research information
# =========================================================

def update_research(
    post_id: int,
    research_summary: str,
    source_urls=None,
) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            UPDATE posts
            SET
                research_summary = ?,
                source_urls = ?,
                updated_at = ?
            WHERE id = ?
            """,
            (
                research_summary,
                serialize_sources(source_urls),
                current_timestamp(),
                post_id,
            ),
        )

        return cursor.rowcount > 0


# =========================================================
# Delete post
# =========================================================

def delete_post(post_id: int) -> bool:
    with get_connection() as conn:
        cursor = conn.execute(
            """
            DELETE FROM posts
            WHERE id = ?
            """,
            (post_id,),
        )

        return cursor.rowcount > 0


# =========================================================
# Statistics
# =========================================================

def get_statistics() -> pd.DataFrame:
    with get_connection() as conn:
        return pd.read_sql_query(
            """
            SELECT
                status,
                COUNT(*) AS total
            FROM posts
            GROUP BY status
            ORDER BY total DESC
            """,
            conn,
        )


# Create and migrate the database when imported.
init_db()