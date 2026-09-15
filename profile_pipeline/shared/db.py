"""DB 连接管理 + schema 初始化。"""

import sqlite3
from pathlib import Path


DB_PATH = Path("/AstrBot/data/profile_data.db")


SCHEMA = [
    """CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id TEXT,
        session_id TEXT NOT NULL,
        group_id TEXT,
        sender_id TEXT,
        sender_name TEXT,
        platform TEXT,
        content TEXT,
        msg_type TEXT DEFAULT 'text',
        timestamp INTEGER,
        raw_payload TEXT,
        captured_at TEXT NOT NULL
    )""",
    """CREATE TABLE IF NOT EXISTS attachments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        attachment_type TEXT,
        local_path TEXT,
        remote_url TEXT,
        file_name TEXT,
        file_size INTEGER,
        mime_type TEXT,
        width INTEGER,
        height INTEGER,
        position INTEGER,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS mentions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        mentioned_user_id TEXT,
        mentioned_name TEXT,
        is_at_all INTEGER DEFAULT 0,
        position INTEGER,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    )""",
    """CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        quoted_text TEXT,
        quoted_type TEXT,
        quoted_summary TEXT,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    )""",
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_msg_time ON messages(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_msg_sender ON messages(sender_id)",
    "CREATE INDEX IF NOT EXISTS idx_att_msg ON attachments(message_id)",
    "CREATE INDEX IF NOT EXISTS idx_men_msg ON mentions(message_id)",
    "CREATE INDEX IF NOT EXISTS idx_qt_msg ON quotes(message_id)",
]


def get_conn():
    """每次新连接（避免 sqlite 多线程问题）。"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # 支持 dict-style 访问
    return conn


def init_db():
    """建表 + 索引。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_conn() as conn:
        for stmt in SCHEMA:
            conn.execute(stmt)
        for idx in INDEXES:
            conn.execute(idx)
        conn.commit()
