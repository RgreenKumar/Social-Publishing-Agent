import sqlite3
from datetime import datetime
import pandas as pd

DB_PATH = "data/post_history.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            update_id INTEGER,
            company TEXT,
            title TEXT,
            platform TEXT,
            draft TEXT,
            status TEXT
        )
    """)

    cursor.execute("PRAGMA table_info(posts)")
    existing_columns = [row[1] for row in cursor.fetchall()]

    if "scheduled_time" not in existing_columns:
        cursor.execute("ALTER TABLE posts ADD COLUMN scheduled_time TEXT")

    if "recommended_time" not in existing_columns:
        cursor.execute("ALTER TABLE posts ADD COLUMN recommended_time TEXT")

    if "publish_mode" not in existing_columns:
        cursor.execute("ALTER TABLE posts ADD COLUMN publish_mode TEXT")

    conn.commit()
    conn.close()


def save_post_history(
    update_id,
    company,
    title,
    platform,
    draft,
    status,
    scheduled_time=None,
    recommended_time=None,
    publish_mode="mock"
):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    cursor.execute("""
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
            publish_mode
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        update_id,
        company,
        title,
        platform,
        draft,
        status,
        scheduled_time,
        recommended_time,
        publish_mode
    ))

    conn.commit()
    conn.close()


def load_post_history():
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM posts ORDER BY id DESC"
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df