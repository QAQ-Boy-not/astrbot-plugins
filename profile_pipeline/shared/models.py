"""领域对象（dataclass）。"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Message:
    """一条聊天消息。"""

    id: Optional[int] = None
    message_id: Optional[str] = None      # 平台消息 ID
    session_id: str = ""                  # 会话 ID
    group_id: Optional[str] = None
    sender_id: Optional[str] = None
    sender_name: Optional[str] = None
    platform: Optional[str] = None
    content: str = ""
    msg_type: str = "text"                # text / image / video / file / sticker / mixed / empty
    timestamp: Optional[int] = None
    raw_payload: Optional[str] = None
    captured_at: str = ""

    # 关联
    attachments: list["Attachment"] = field(default_factory=list)
    mentions: list["Mention"] = field(default_factory=list)
    quotes: list["Quote"] = field(default_factory=list)

    @classmethod
    def user_message(
        cls,
        *,
        message_id: str,
        session_id: str,
        content: str,
        group_id: str = "",
        sender_id: str = "",
        sender_name: str = "",
        platform: str = "",
        msg_type: str = "text",
        timestamp: int = 0,
        raw_payload: Optional[str] = None,
    ) -> "Message":
        """工厂方法：构造一条用户消息。"""
        return cls(
            message_id=message_id,
            session_id=session_id,
            group_id=group_id,
            sender_id=sender_id,
            sender_name=sender_name,
            platform=platform,
            content=content,
            msg_type=msg_type,
            timestamp=timestamp,
            raw_payload=raw_payload,
            captured_at=datetime.now().isoformat(timespec="seconds"),
        )

    def short_preview(self, max_len: int = 50) -> str:
        """给日志用。"""
        s = self.content.replace("\n", " ")
        return s if len(s) <= max_len else s[: max_len - 3] + "..."


@dataclass
class Attachment:
    """附件（图片/视频/文件/表情包）。"""

    id: Optional[int] = None
    message_id: Optional[int] = None
    attachment_type: str = ""              # image / video / file / sticker
    local_path: str = ""
    remote_url: str = ""
    file_name: str = ""
    file_size: Optional[int] = None
    mime_type: str = ""
    width: Optional[int] = None
    height: Optional[int] = None
    position: int = 0


@dataclass
class Mention:
    """@ 提及。"""

    id: Optional[int] = None
    message_id: Optional[int] = None
    mentioned_user_id: str = ""
    mentioned_name: str = ""
    is_at_all: bool = False
    position: int = 0


@dataclass
class Quote:
    """引用回复（数据降级——原消息 ID 拿不到）。"""

    id: Optional[int] = None
    message_id: Optional[int] = None
    quoted_text: str = ""
    quoted_type: str = "text"              # text / non-text
    quoted_summary: str = ""
