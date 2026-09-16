## Context

参考 proposal.md 了解动机。技术约束：
- AstrBot 4.27.4 的插件只能 `@filter.event_message_type(EventMessageType.ALL)` 拿到所有消息（实战验证通过）
- AstrBotMessage.message_chain 是结构化 List[BaseMessageComponent]
- Reply 组件不暴露原消息 ID（实测：id="", qq=0）
- 当前项目已有 `tools/sqlite-toolkit` Skill 用于本地探查 SQLite

## Goals / Non-Goals

**Goals:**
- 实现一个独立的 plugin，只负责"消息→数据库"这一段
- 不影响 AstrBot 自身的 conversations.content / platform_message_history
- 表结构遵循 3NF（messages / attachments / mentions / quotes）
- 解析逻辑严格按 message_chain component 类型分桶

**Non-Goals:**
- 不抓 assistant 回复（属 Phase 2）
- 不做 LLM 提取（属 Phase 2）
- 不做上下文注入（属 Phase 3）
- 不写 KB（属 Phase 2）

## Decisions

### 1. 单一 plugin 文件结构

profile_generator 的所有逻辑（schema + 钩子 + 解析）放在一个 `main.py`，~120 行。

**为什么**：Phase 1 范围小，分多个文件增加阅读成本。Phase 2/3 加功能时再考虑拆分。

### 2. DB 文件路径：/AstrBot/data/profile_data.db

独立于 AstrBot 自己的 data_v4.db，避免命名/索引冲突。

**为什么**：
- 主键 `id` 不冲突
- schema 完全可控
- 删 plugin 时直接 rm 文件即可，不污染 AstrBot 数据

### 3. 用 sqlite3 内置模块，不用 SQLAlchemy

**为什么**：
- 数据量小（每天最多几百条消息）
- 单 plugin 单 DB，不需要 ORM
- 减少依赖

### 4. RAW Payload 存 JSON（messages.raw_payload）

**为什么**：
- 实战发现 raw_message 含 mentions/attachments/message_reference 等详细字段
- 4 张表存不下所有字段
- JSON 字段保留"全量备份"，未来需要可解析
- 不要"过度规范化"

### 5. quoted_message_id 字段不存（Qu 字段名降级）

**为什么**：
- 实测 Reply.id == ""，AstrBot 不暴露原消息 ID
- 强行存一个空字段没意义
- 只存 quoted_text + quoted_type

### 6. 错误处理：try-except 包整个钩子

**为什么**：
- 不能因为插件挂了导致 bot 整体挂
- 失败只记日志，不抛异常

## Risks / Trade-offs

- **风险 1：raw_message 是 dict 嵌套结构，序列化可能很大** → 限制为前 50KB（足够覆盖正常场景）
- **风险 2：图片本地路径 /AstrBot/data/temp/xxx 可能被 AstrBot 清理** → 不影响：反正 path 只存"曾经有附件"的事实
- **风险 3：每次消息都打开 sqlite 连接** → 用 with context manager（自动关闭），性能足够

## Migration Plan

无（独立新文件，没有迁移负担）

## Open Questions

- 表情包（Face component）的精确结构未实测——按 Plain 文本嵌入 `[表情:id]` 处理，未来需要时再细化
- 性能：当前每天消息量 < 1000，未做性能优化；如未来 > 10K/天再考虑批写入
