# CLAUDE.md - inspect_response 插件

## 项目背景

**inspect_response** 是 AstrBot 调试插件，**纯旁路监听**，不修改任何数据流。

**核心功能**：
1. `on_llm_request` 钩子 → 打印**完整**发送给大模型的 JSON（不截断）
2. `on_llm_response` 钩子 → 打印大模型返回的完整结构

**v1.0.0 范围**：仅打印，不修改任何字段。

## 关键路径映射

| 用途 | 主机路径（公司服务器） | 容器内路径 |
|------|---------------------|-----------|
| 插件目录 | `./data/plugins/inspect_response/` | `/AstrBot/data/plugins/inspect_response/` |
| 完整请求 JSON 落地 | 同上目录 | `last_request.json` |

## 核心实现要点

### on_llm_request：打印完整 JSON

```python
# 1. safe_dump 处理 pydantic/dataclass/嵌套对象
# 2. json.dumps(ensure_ascii=False, indent=2) 保留中文
# 3. 逐行 print + 同时写文件 last_request.json
```

### on_llm_response：打印原始响应

```python
# 重点看 raw_completion.model_dump()
# 自动尝试 model_dump / dict / to_dict 三种方法
```

## 调试流程

1. **触发对话**：用户发消息给机器人
2. **看 docker logs**：`docker logs -f astrbot | grep inspect_response`
3. **或读文件**：`cat /AstrBot/data/plugins/inspect_response/last_request.json`

## 数据结构要点

基于 `astrbot/core/provider/entities.py` 源码：

- `req.contexts`: `list[dict]` OpenAI 格式消息数组
- `req.conversation`: `Conversation` 会话对象（非消息列表）
- `req.system_prompt`: `str`
- `req.prompt`: 用户原始消息 str
- `req.extra_user_content_parts`: `list[ContentPart]`
- `req.func_tool`: `ToolSet`
- `req.model`: 模型名

## 文件清单

```
inspect_response/
├── main.py            (406 行，含 on_llm_request + on_llm_response)
├── metadata.yaml
├── README.md
└── CLAUDE.md
```

## 调试记录

### v1.0.0 — 2026-08-27

- 实现 on_llm_request + on_llm_response 双钩子
- 完整 JSON 不截断
- 同时落地到 `last_request.json` 方便事后查阅