"""profile_generator - Phase 1: 数据捕获

只做一件事：把群里所有消息（原原本本）写入自有数据库。
不做画像提取、不做上下文注入。

钩子：event_message_type(EventMessageType.ALL)
DB：  /AstrBot/data/profile_data.db
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# 让 shared 能 import
sys.path.insert(0, str(Path(__file__).parent.parent))

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.core.message.components import Plain, At, Image, Video, Reply
from astrbot.core.star.filter.event_message_type import EventMessageType

from shared.db import init_db
from shared.models import Message, Attachment, Mention, Quote
from shared.message_repository import MessageRepository


def _safe_str(v, default=""):
    return str(v) if v is not None else default


def extract_message(msg):
    """从 AstrBotMessage 构造 Message 对象（包含 attachments/mentions/quotes）。"""
    chain = msg.message or []
    text_parts = []
    attachments = []
    mentions = []
    quotes = []

    for i, comp in enumerate(chain):
        if isinstance(comp, Plain):
            text_parts.append(comp.text or "")
        elif isinstance(comp, At):
            qq = _safe_str(getattr(comp, "qq", ""))
            mentions.append(Mention(
                mentioned_user_id=qq,
                mentioned_name=_safe_str(getattr(comp, "name", "")),
                is_at_all=(qq == "all"),
                position=i,
            ))
        elif isinstance(comp, Image):
            attachments.append(Attachment(
                attachment_type="image",
                local_path=_safe_str(getattr(comp, "path", "")),
                remote_url="",
                file_name="",
                file_size=None,
                mime_type="image/jpeg",
                width=None, height=None,
                position=i,
            ))
        elif isinstance(comp, Video):
            attachments.append(Attachment(
                attachment_type="video",
                local_path="",
                remote_url=_safe_str(getattr(comp, "file", "")),
                file_name="",
                file_size=None,
                mime_type="video/mp4",
                width=None, height=None,
                position=i,
            ))
        elif isinstance(comp, Reply):
            qtext = _safe_str(getattr(comp, "text", ""))
            quotes.append(Quote(
                quoted_text=qtext,
                quoted_type="text" if qtext else "non-text",
                quoted_summary=qtext or "[非文本引用]",
            ))
        else:
            cid = getattr(comp, "id", None)
            if cid:
                text_parts.append(f"[表情:{cid}]")

    content = "".join(text_parts)
    has_stuff = bool(attachments or mentions or quotes)
    if has_stuff:
        msg_type = "mixed"
    elif content:
        msg_type = "text"
    else:
        msg_type = "empty"

    return Message(
        message_id=_safe_str(getattr(msg, "message_id", None)),
        session_id=_safe_str(getattr(msg, "session_id", "")),
        group_id=_safe_str(getattr(msg, "group_id", "")),
        sender_id=_safe_str(getattr(getattr(msg, "sender", None), "user_id", "")),
        sender_name=_safe_str(getattr(getattr(msg, "sender", None), "nickname", "")),
        platform=_safe_str(getattr(msg, "self_id", "")),
        content=content,
        msg_type=msg_type,
        timestamp=getattr(msg, "timestamp", None),
        captured_at=datetime.now().isoformat(timespec="seconds"),
        attachments=attachments,
        mentions=mentions,
        quotes=quotes,
    )


@register("profile_generator", "anonymous", "捕获群里所有消息到自有数据库（个人学习项目）", "0.2.0-20260916-100129")
class ProfileGenerator(Star):
    def __init__(self, context: Context):
        super().__init__(context)
        init_db()
        self.repo = MessageRepository()

    async def initialize(self):
        pass

    async def terminate(self):
        pass

    @filter.event_message_type(EventMessageType.ALL)
    async def capture_all(self, event: AstrMessageEvent):
        """捕获群里所有消息。"""
        try:
            msg = extract_message(event.message_obj)
            msg.raw_payload = _safe_raw(event.message_obj)
            self.repo.insert(msg)
        except Exception as e:
            from astrbot import logger
            logger.error(f"[profile_generator] capture failed: {e}")


def _safe_raw(msg):
    """备份 raw_message 到 raw_payload。"""
    try:
        return json.dumps(
            {
                "raw_message": str(getattr(msg, "raw_message", ""))[:50000],
                "chain_length": len(getattr(msg, "message", []) or []),
            },
            ensure_ascii=False,
            default=str,
        )
    except Exception:
        return None
