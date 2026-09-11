"""inspect_response v2.0.0 - 4 点全链路打印

打印时机（按消息生命周期）：
 1. event_message_type(ALL)  → 原始消息（AstrBotMessage）
 2. on_llm_request           → LLM 看到的请求
 3. on_llm_response          → LLM 返回的响应
 4. on_decorating_result     → 最终装饰后

每个用 sys.stdout.write 一次性输出 JSON。
"""

import json
import sys

from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import ProviderRequest, LLMResponse
from astrbot.core.star.filter.event_message_type import EventMessageType


@register("inspect_response", "wangjing", "全链路 4 点打印（原始消息 / LLM 请求 / LLM 响应 / 最终输出）", "2.0.0")
class InspectResponsePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        pass

    # ---------- 通用工具 ----------

    def _print_json(self, tag: str, data: dict):
        """一次性输出 JSON，tag 标识阶段。"""
        payload = {"[inspect_response]": tag, **data}
        sys.stdout.write("\n" + json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n")
        sys.stdout.flush()

    def _safe_dump(self, obj, depth=0, max_depth=8, _seen=None):
        """递归把对象转成 dict/list/原生类型。"""
        if _seen is None:
            _seen = set()
        obj_id = id(obj)
        if obj_id in _seen:
            return "<循环引用>"
        _seen.add(obj_id)
        if depth > max_depth:
            return f"<深度超过 {max_depth}>"
        if obj is None or isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, bytes):
            try:
                return obj.decode("utf-8", errors="replace")
            except Exception:
                return f"<bytes len={len(obj)}>"
        if isinstance(obj, dict):
            return {str(k): self._safe_dump(v, depth + 1, max_depth, _seen) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set, frozenset)):
            return [self._safe_dump(v, depth + 1, max_depth, _seen) for v in obj]
        if hasattr(obj, "model_dump"):
            try:
                return self._safe_dump(obj.model_dump(), depth + 1, max_depth, _seen)
            except Exception:
                pass
        if hasattr(obj, "__dataclass_fields__"):
            try:
                fields = {k: getattr(obj, k) for k in obj.__dataclass_fields__}
                return self._safe_dump(fields, depth + 1, max_depth, _seen)
            except Exception:
                pass
        try:
            return str(obj)
        except Exception:
            return f"<无法序列化 {type(obj).__name__}>"

    def _dump_message_chain(self, message_list):
        """把 message 链（List[BaseMessageComponent]）转成结构化 JSON。"""
        if not message_list:
            return []
        result = []
        for comp in message_list:
            item = {
                "type": getattr(comp, "type", "?"),
                "class": type(comp).__name__,
            }
            # 各种组件的关键字段
            for attr in ("text", "qq", "id", "name", "url", "file", "path", "summary"):
                if hasattr(comp, attr):
                    item[attr] = getattr(comp, attr)
            # 嵌套字段（image 的 url 子对象）
            for nested in ("image", "audio", "video"):
                if hasattr(comp, nested):
                    sub = getattr(comp, nested)
                    if sub is not None:
                        item[nested] = self._safe_dump(sub)
            result.append(item)
        return result

    # ---------- 打印点 1：原始消息 ----------

    @filter.event_message_type(EventMessageType.ALL)
    async def inspect_raw_message(self, event: AstrMessageEvent):
        """打印 AstrBot 接收到的原始消息（AstrBotMessage）。"""
        msg = event.message_obj
        data = {
            "stage": "1_raw_message",
            "trigger_reason": "event_message_type(ALL)",
            "astrobot_message": {
                "type": str(getattr(msg, "type", None)),
                "self_id": getattr(msg, "self_id", None),
                "session_id": getattr(msg, "session_id", None),
                "message_id": getattr(msg, "message_id", None),
                "group_id": getattr(msg, "group_id", None),
                "sender": self._safe_dump(getattr(msg, "sender", None)),
                "message_chain": self._dump_message_chain(getattr(msg, "message", [])),
                "message_str": getattr(msg, "message_str", None),
                "raw_message": self._safe_dump(getattr(msg, "raw_message", None)),
                "timestamp": getattr(msg, "timestamp", None),
            },
        }
        self._print_json("1.原始消息", data)

    # ---------- 打印点 2：LLM 请求 ----------

    @filter.on_llm_request()
    async def inspect_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        """打印 LLM 实际看到的请求。"""
        data = {
            "stage": "2_llm_request",
            "prompt": req.prompt,
            "session_id": req.session_id,
            "model": req.model,
            "image_urls": req.image_urls,
            "audio_urls": req.audio_urls,
            "extra_user_content_parts": self._safe_dump(req.extra_user_content_parts),
            "func_tool": self._safe_dump(req.func_tool),
            "system_prompt": req.system_prompt,
            "contexts_count": len(req.contexts) if req.contexts else 0,
            "tool_calls_result": self._safe_dump(req.tool_calls_result),
        }
        self._print_json("2.LLM 请求", data)

    # ---------- 打印点 3：LLM 响应 ----------

    @filter.on_llm_response()
    async def inspect_llm_response(self, event: AstrMessageEvent, response: LLMResponse):
        """打印 LLM 返回的响应。"""
        data = {
            "stage": "3_llm_response",
            "role": getattr(response, "role", None),
            "completion_text": getattr(response, "completion_text", None),
            "tools_call_args": getattr(response, "tools_call_args", None),
            "tools_call_name": getattr(response, "tools_call_name", None),
            "tools_call_ids": getattr(response, "tools_call_ids", None),
            "reasoning_content": getattr(response, "reasoning_content", None),
            "raw_completion": self._safe_dump(getattr(response, "raw_completion", None)),
            "usage": self._safe_dump(getattr(response, "usage", None)),
        }
        self._print_json("3.LLM 响应", data)

    # ---------- 打印点 4：最终装饰 ----------

    @filter.on_decorating_result()
    async def inspect_decorating(self, event: AstrMessageEvent):
        """打印最终装饰后的结果（bot 实际要发送的内容）。"""
        # event.result 是最终结果链
        data = {
            "stage": "4_decorating_result",
            "result_chain": self._safe_dump(getattr(event, "result", None)),
            "result_message_str": getattr(getattr(event, "result", None), "message_str", None),
        }
        self._print_json("4.最终输出", data)

    async def terminate(self):
        pass
