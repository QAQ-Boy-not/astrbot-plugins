"""profile_generator - Phase 1: 数据捕获

只做一件事：把群里所有消息（原原本本）写入自有数据库。
不做画像提取、不做上下文注入。

钩子：event_message_type(EventMessageType.ALL)
DB：  /AstrBot/data/profile_data.db
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.message.components import Plain, At, Image, Video, Reply
from astrbot.core.star.filter.event_message_type import EventMessageType


DB_PATH = Path("/AstrBot/data/profile_data.db")

# 4 张表 schema（3NF）
SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS messages (
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS attachments (
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
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS mentions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        mentioned_user_id TEXT,
        mentioned_name TEXT,
        is_at_all INTEGER DEFAULT 0,
        position INTEGER,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS quotes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        message_id INTEGER NOT NULL,
        quoted_text TEXT,
        quoted_type TEXT,
        quoted_summary TEXT,
        FOREIGN KEY (message_id) REFERENCES messages(id) ON DELETE CASCADE
    )
    """,
]

INDEXES = [
    "CREATE INDEX IF NOT EXISTS idx_msg_session ON messages(session_id)",
    "CREATE INDEX IF NOT EXISTS idx_msg_time ON messages(timestamp)",
    "CREATE INDEX IF NOT EXISTS idx_msg_sender ON messages(sender_id)",
    "CREATE INDEX IF NOT EXISTS idx_att_msg ON attachments(message_id)",
    "CREATE INDEX IF NOT EXISTS idx_men_msg ON mentions(message_id)",
    "CREATE INDEX IF NOT EXISTS idx_qt_msg ON quotes(message_id)",
]


def init_db():
    """建表 + 索引。"""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DB_PATH) as conn:
        for stmt in SCHEMA:
            conn.execute(stmt)
        for idx in INDEXES:
            conn.execute(idx)
        conn.commit()


def get_conn():
    """获取新连接（每次新连接避免线程问题）。"""
    return sqlite3.connect(DB_PATH)


def _safe_str(v, default=""):
    return str(v) if v is not None else default


def extract_message_chain(msg):
    """解析 AstrBotMessage.message_chain，按 component 类型分桶。

    Returns:
        dict {
            'text_parts': list[str],
            'attachments': list[dict],
            'mentions': list[dict],
            'quotes': list[dict],
            'msg_type': str,
        }
    """
    chain = msg.message or []
    text_parts = []
    attachments = []
    mentions = []
    quotes = []

    for i, comp in enumerate(chain):
        if isinstance(comp, Plain):
            text_parts.append(comp.text or "")
        elif isinstance(comp, At):
            mentions.append({
                "user_id": _safe_str(getattr(comp, "qq", "")),
                "name": _safe_str(getattr(comp, "name", "")),
                "is_at_all": _safe_str(getattr(comp, "qq", "")) == "all",
                "position": i,
            })
        elif isinstance(comp, Image):
            attachments.append({
                "type": "image",
                "local_path": _safe_str(getattr(comp, "path", "")),
                "remote_url": "",
                "file_name": "",
                "file_size": None,
                "mime_type": "image/jpeg",
                "width": None,
                "height": None,
                "position": i,
            })
        elif isinstance(comp, Video):
            attachments.append({
                "type": "video",
                "local_path": "",
                "remote_url": _safe_str(getattr(comp, "file", "")),
                "file_name": "",
                "file_size": None,
                "mime_type": "video/mp4",
                "width": None,
                "height": None,
                "position": i,
            })
        elif isinstance(comp, Reply):
            qtext = _safe_str(getattr(comp, "text", ""))
            quotes.append({
                "quoted_text": qtext,
                "quoted_type": "text" if qtext else "non-text",
                "quoted_summary": qtext or "[非文本引用]",
            })
        else:
            # Face 或其他：文本占位
            cid = getattr(comp, "id", None)
            if cid:
                text_parts.append(f"[表情:{cid}]")

    content = "".join(text_parts)
    has_att = bool(attachments)
    has_men = bool(mentions)
    has_qt = bool(quotes)
    if has_att or has_men or has_qt:
        msg_type = "mixed"
    elif content:
        msg_type = "text"
    else:
        msg_type = "empty"

    return {
        "text_parts": text_parts,
        "content": content,
        "attachments": attachments,
        "mentions": mentions,
        "quotes": quotes,
        "msg_type": msg_type,
    }


@register("profile_generator", "wangjing", "捕获群里所有消息到自有数据库（个人学习项目）", "0.1.0")
class ProfileGenerator(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        init_db()

    async def initialize(self):
        pass

    async def terminate(self):
        pass

    @filter.event_message_type(EventMessageType.ALL)
    async def capture_all(self, event: AstrMessageEvent):
        """捕获群里所有消息，写入 4 张表。"""
        try:
            msg = event.message_obj
            parsed = extract_message_chain(msg)
            raw = json.dumps(_safe_dump_raw(msg), ensure_ascii=False, default=str)[:50000]

            with get_conn() as conn:
                cur = conn.execute(
                    """INSERT INTO messages
                       (message_id, session_id, group_id, sender_id, sender_name,
                        platform, content, msg_type, timestamp, raw_payload, captured_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        _safe_str(getattr(msg, "message_id", None)),
                        _safe_str(getattr(msg, "session_id", "")),
                        _safe_str(getattr(msg, "group_id", "")),
                        _safe_str(getattr(getattr(msg, "sender", None), "user_id", "")),
                        _safe_str(getattr(getattr(msg, "sender", None), "nickname", "")),
                        _safe_str(getattr(msg, "self_id", "")),
                        parsed["content"],
                        parsed["msg_type"],
                        getattr(msg, "timestamp", None),
                        raw,
                        datetime.now().isoformat(timespec="seconds"),
                    ),
                )
                msg_id = cur.lastrowid

                for att in parsed["attachments"]:
                    conn.execute(
                        """INSERT INTO attachments
                           (message_id, attachment_type, local_path, remote_url,
                            file_name, file_size, mime_type, width, height, position)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            msg_id, att["type"], att["local_path"], att["remote_url"],
                            att["file_name"], att["file_size"], att["mime_type"],
                            att["width"], att["height"], att["position"],
                        ),
                    )

                for men in parsed["mentions"]:
                    conn.execute(
                        """INSERT INTO mentions
                           (message_id, mentioned_user_id, mentioned_name, is_at_all, position)
                           VALUES (?, ?, ?, ?, ?)""",
                        (
                            msg_id, men["user_id"], men["name"],
                            1 if men["is_at_all"] else 0, men["position"],
                        ),
                    )

                for qt in parsed["quotes"]:
                    conn.execute(
                        """INSERT INTO quotes
                           (message_id, quoted_text, quoted_type, quoted_summary)
                           VALUES (?, ?, ?, ?)""",
                        (
                            msg_id, qt["quoted_text"],
                            qt["quoted_type"], qt["quoted_summary"],
                        ),
                    )

                conn.commit()
        except Exception as e:
            # 错误只记日志，不抛异常（不影响 bot 主流程）
            from astrbot import logger
            logger.error(f"[profile_generator] capture failed: {e}")


def _safe_dump_raw(msg):
    """把 AstrBotMessage 转成 dict，用于 raw_payload 备份。"""
    try:
        return {
            "message_id": getattr(msg, "message_id", None),
            "raw_message": str(getattr(msg, "raw_message", None))[:50000],
            "sender": _safe_str(getattr(getattr(msg, "sender", None), "user_id", "")),
            "chain_length": len(getattr(msg, "message", []) or []),
        }
    except Exception:
        return {}
