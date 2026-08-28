from astrbot.api.event import filter, AstrMessageEvent
from astrbot.api.star import Context, Star, register
from astrbot.api.provider import ProviderRequest

import json
import sys


@register("inspect_response", "your_name", "打印大模型请求/响应的完整 JSON", "1.0.0")
class InspectResponsePlugin(Star):
    def __init__(self, context: Context):
        super().__init__(context)

    async def initialize(self):
        """插件初始化"""
        pass

    def _safe_dump(self, obj, depth=0, max_depth=8, _seen=None):
        """递归把对象转成可 JSON 序列化的 dict/list/原生类型"""
        if _seen is None:
            _seen = set()
        obj_id = id(obj)
        if obj_id in _seen:
            return f"<循环引用>"
        _seen.add(obj_id)
        if depth > max_depth:
            return f"<深度超过 {max_depth}>"
        if obj is None:
            return None
        if isinstance(obj, (str, int, float, bool)):
            return obj
        if isinstance(obj, bytes):
            try:
                return obj.decode('utf-8', errors='replace')
            except Exception:
                return f"<bytes len={len(obj)}>"
        if isinstance(obj, dict):
            return {str(k): self._safe_dump(v, depth + 1, max_depth, _seen) for k, v in obj.items()}
        if isinstance(obj, (list, tuple, set, frozenset)):
            return [self._safe_dump(v, depth + 1, max_depth, _seen) for v in obj]
        if hasattr(obj, 'model_dump'):
            try:
                return self._safe_dump(obj.model_dump(), depth + 1, max_depth, _seen)
            except Exception:
                pass
        if hasattr(obj, 'dict') and callable(obj.dict):
            try:
                return self._safe_dump(obj.dict(), depth + 1, max_depth, _seen)
            except Exception:
                pass
        if hasattr(obj, '__dataclass_fields__'):
            try:
                fields = {k: getattr(obj, k) for k in obj.__dataclass_fields__}
                return self._safe_dump(fields, depth + 1, max_depth, _seen)
            except Exception:
                pass
        try:
            return str(obj)
        except Exception:
            return f"<无法序列化 {type(obj).__name__}>"

    def _conv_dump(self, conv):
        """把 Conversation 对象转成 dict（避免 dump 整个 history 字符串）"""
        if conv is None:
            return None
        return {
            "platform_id": getattr(conv, 'platform_id', None),
            "user_id": getattr(conv, 'user_id', None),
            "cid": getattr(conv, 'cid', None),
            "title": getattr(conv, 'title', None),
            "persona_id": getattr(conv, 'persona_id', None),
            "created_at": getattr(conv, 'created_at', None),
            "updated_at": getattr(conv, 'updated_at', None),
            "token_usage": getattr(conv, 'token_usage', None),
            "history": getattr(conv, 'history', None),
        }

    def _print_json(self, json_str):
        """一次性打印完整 JSON，不切行"""
        sys.stdout.write("\n" + json_str + "\n")
        sys.stdout.flush()

    @filter.on_llm_request(priority=-100)
    async def inspect_llm_request(self, event: AstrMessageEvent, req: ProviderRequest):
        """只打印完整请求 JSON（一次输出）"""
        request_data = {
            "prompt": req.prompt,
            "session_id": req.session_id,
            "model": req.model,
            "image_urls": req.image_urls,
            "audio_urls": req.audio_urls,
            "extra_user_content_parts": self._safe_dump(req.extra_user_content_parts),
            "func_tool": self._safe_dump(req.func_tool),
            "contexts": self._safe_dump(req.contexts),
            "system_prompt": req.system_prompt,
            "conversation": self._conv_dump(req.conversation),
            "tool_calls_result": self._safe_dump(req.tool_calls_result),
        }
        self._print_json(json.dumps(request_data, ensure_ascii=False, indent=2))

    @filter.on_llm_response(priority=-100)
    async def inspect_llm_response(self, event: AstrMessageEvent, response):
        """只打印完整响应 JSON（一次输出）"""
        response_data = {
            "role": getattr(response, 'role', None),
            "completion_text": getattr(response, 'completion_text', None),
            "result_chain": self._safe_dump(getattr(response, 'result_chain', None)),
            "tools_call_args": getattr(response, 'tools_call_args', None),
            "tools_call_name": getattr(response, 'tools_call_name', None),
            "tools_call_ids": getattr(response, 'tools_call_ids', None),
            "tools_call_extra_content": getattr(response, 'tools_call_extra_content', None),
            "reasoning_content": getattr(response, 'reasoning_content', None),
            "reasoning_signature": getattr(response, 'reasoning_signature', None),
            "raw_completion": self._safe_dump(getattr(response, 'raw_completion', None)),
            "is_chunk": getattr(response, 'is_chunk', None),
            "id": getattr(response, 'id', None),
            "usage": self._safe_dump(getattr(response, 'usage', None)),
        }
        self._print_json(json.dumps(response_data, ensure_ascii=False, indent=2))

    async def terminate(self):
        """插件销毁"""
        pass