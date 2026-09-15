"""Message Repository - messages 表的所有操作。"""

from .db import get_conn
from .models import Message


class MessageRepository:
    """消息表的 CRUD + 查询。"""

    def insert(self, msg: Message) -> int:
        """插入一条消息，返回 id。同时插入关联的 attachments/mentions/quotes。"""
        with get_conn() as conn:
            cur = conn.execute(
                """INSERT INTO messages
                   (message_id, session_id, group_id, sender_id, sender_name,
                    platform, content, msg_type, timestamp, raw_payload, captured_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    msg.message_id, msg.session_id, msg.group_id,
                    msg.sender_id, msg.sender_name, msg.platform,
                    msg.content, msg.msg_type, msg.timestamp,
                    msg.raw_payload, msg.captured_at,
                ),
            )
            msg_id = cur.lastrowid

            for att in msg.attachments:
                conn.execute(
                    """INSERT INTO attachments
                       (message_id, attachment_type, local_path, remote_url,
                        file_name, file_size, mime_type, width, height, position)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (msg_id, att.attachment_type, att.local_path, att.remote_url,
                     att.file_name, att.file_size, att.mime_type,
                     att.width, att.height, att.position),
                )

            for men in msg.mentions:
                conn.execute(
                    """INSERT INTO mentions
                       (message_id, mentioned_user_id, mentioned_name, is_at_all, position)
                       VALUES (?, ?, ?, ?, ?)""",
                    (msg_id, men.mentioned_user_id, men.mentioned_name,
                     1 if men.is_at_all else 0, men.position),
                )

            for qt in msg.quotes:
                conn.execute(
                    """INSERT INTO quotes
                       (message_id, quoted_text, quoted_type, quoted_summary)
                       VALUES (?, ?, ?, ?)""",
                    (msg_id, qt.quoted_text, qt.quoted_type, qt.quoted_summary),
                )

            conn.commit()
            return msg_id

    def list_by_session(self, session_id: str, limit: int = 100) -> list[Message]:
        """按 session 查最近 N 条。"""
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE session_id = ?
                   ORDER BY id DESC LIMIT ?""",
                (session_id, limit),
            ).fetchall()
        return [self._to_model(r) for r in rows]

    def list_recent(self, days: int = 3, limit: int = 1000) -> list[Message]:
        """最近 N 天的所有消息。"""
        with get_conn() as conn:
            rows = conn.execute(
                """SELECT * FROM messages
                   WHERE timestamp > strftime('%s', 'now', ?)
                   ORDER BY id DESC LIMIT ?""",
                (f"-{days} days", limit),
            ).fetchall()
        return [self._to_model(r) for r in rows]

    def count_by_sender(self, session_id: str | None = None) -> dict[str, int]:
        """每个 sender 的消息数。"""
        with get_conn() as conn:
            if session_id:
                rows = conn.execute(
                    """SELECT sender_name, COUNT(*) AS cnt FROM messages
                       WHERE session_id = ? GROUP BY sender_name""",
                    (session_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """SELECT sender_name, COUNT(*) AS cnt FROM messages
                       GROUP BY sender_name"""
                ).fetchall()
        return {r["sender_name"] or "(unknown)": r["cnt"] for r in rows}

    def _to_model(self, row) -> Message:
        return Message(
            id=row["id"],
            message_id=row["message_id"],
            session_id=row["session_id"],
            group_id=row["group_id"],
            sender_id=row["sender_id"],
            sender_name=row["sender_name"],
            platform=row["platform"],
            content=row["content"] or "",
            msg_type=row["msg_type"] or "text",
            timestamp=row["timestamp"],
            raw_payload=row["raw_payload"],
            captured_at=row["captured_at"] or "",
        )
