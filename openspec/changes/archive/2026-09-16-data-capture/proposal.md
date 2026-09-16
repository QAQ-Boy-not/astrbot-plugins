## Why

profile_pipeline 项目要自建"用户画像系统"，让 bot 真正理解每个用户。但 AstrBot 默认只捕获 @bot 触发的 LLM 调用上下文，群聊里的普通对话完全丢失——这意味着画像系统缺了 99% 的数据。

## What Changes

- 新建 `profile_generator` 插件
- 用 `@filter.event_message_type(EventMessageType.ALL)` 钩子捕获群里所有消息
- 4 张表（messages / attachments / mentions / quotes）落地 3NF schema
- 按 message_chain component 类型分桶解析（Plain / At / Image / Video / Reply）
- 不动 AstrBot 原数据，不动 conversations.content

## Capabilities

### New Capabilities
- `data-capture`: profile_generator 插件的 Phase 1 — 群里所有消息全量入库

### Modified Capabilities
- 无

## Impact

- 新增：profile_pipeline/profile_generator/main.py + 4 张表 schema
- 新增：DB 文件 /AstrBot/data/profile_data.db
- 不影响：AstrBot 原 conversations.content、不影响 inspect_response、不影响 KB 系统
- Phase 2 / Phase 3 不在本 change 范围（后续 change 跟进）
