from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import ProviderRequest


@register("info_extend", "your_name", "向大模型注入用户消息上下文（User ID/Nickname/Group）", "1.3.0")
class InfoExtendPlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        pass

    @filter.on_llm_request()
    async def inject_message_context(self, event: AstrMessageEvent, req: ProviderRequest):
        """静默向 extra_user_content_parts 追加用户消息上下文 XML

        输出格式（模仿 napcat）：
            群聊：<system_reminder>User ID: ..., Nickname: ...
                      Group name: ...</system_reminder>
            私聊：<system_reminder>User ID: ..., Nickname: ...
                      Session type: 私聊</system_reminder>

        时间字段不加（AstrBot 系统会自动注入 Current datetime）。
        """
        sender_id = event.get_sender_id() or "未知"
        sender_name = event.get_sender_name() or "未知"

        is_private = False
        group_name = ""
        try:
            umo = str(getattr(event, 'unified_msg_origin', ''))
            if 'PrivateMessage' in umo:
                is_private = True
            if hasattr(event, 'get_group_name'):
                try:
                    group_name = event.get_group_name() or ""
                except Exception:
                    pass
            if not group_name and umo:
                parts = umo.split(':')
                if parts:
                    group_name = parts[0]
        except Exception:
            pass

        first_line = f"<system_reminder>[info_extend-v1.3.0] User ID: {sender_id}, Nickname: {sender_name}"
        if is_private:
            second_line = "Session type: 私聊</system_reminder>"
        else:
            second_line = f"Group name: {group_name}</system_reminder>"

        context_xml = first_line + "\n" + second_line

        if req.extra_user_content_parts is None:
            req.extra_user_content_parts = []

        try:
            from astrbot.core.agent.message import TextPart
            req.extra_user_content_parts.append(TextPart(text=context_xml))
        except Exception:
            req.extra_user_content_parts.append({"type": "text", "text": context_xml})

    async def terminate(self):
        pass