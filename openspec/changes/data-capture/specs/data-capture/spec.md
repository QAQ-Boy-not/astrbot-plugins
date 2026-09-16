## Purpose

让 profile_generator 插件能捕获群聊里所有消息（不管 @不@bot），按结构化字段写入自有数据库，为画像提取提供完整数据基础。

## ADDED Requirements

### Requirement: 捕获所有平台消息

profile_generator 插件 SHALL 通过 `@filter.event_message_type(EventMessageType.ALL)` 钩子捕获群聊里所有消息，包括普通消息、@bot 消息、附件消息、引用消息。

#### Scenario: 普通文本消息入库
- **WHEN** 群成员发送纯文本消息（不 @bot）
- **THEN** 消息被写入 messages 表，role=user，content 为文本内容

#### Scenario: @bot 消息入库
- **WHEN** 群成员发送 @bot 的消息
- **THEN** 消息被写入 messages 表，同时 mentions 表记录被 @ 的用户

#### Scenario: 图片消息入库
- **WHEN** 群成员发送图片
- **THEN** messages 表 content 为空字符串，attachments 表新增 image 记录（type=image, local_path=/AstrBot/data/temp/...）

#### Scenario: 视频消息入库
- **WHEN** 群成员发送视频
- **THEN** messages 表 content 为空，attachments 表新增 video 记录（type=video, remote_url=远端 QQ URL）

#### Scenario: 引用回复入库
- **WHEN** 群成员引用另一条消息并回复
- **THEN** messages 表 content 为当前文本，quotes 表记录被引用的内容（仅文字/类型，原消息 ID 拿不到）

### Requirement: 按 message_chain component 类型分别存储

插件 SHALL 遍历 AstrBotMessage.message_chain，按 component 类型分别处理：
- Plain → 拼到 messages.content
- At → 写入 mentions 表
- Image / Video / File → 写入 attachments 表
- Reply → 写入 quotes 表

#### Scenario: 多 component 消息正确拆分
- **WHEN** 消息包含 At + Plain（如 `@bot 你好`）
- **THEN** mentions 表记录 1 条 mention，messages.content 为"你好"

#### Scenario: 图片消息无文本污染
- **WHEN** 消息只有 Image component
- **THEN** messages.content 为空字符串，attachments 表有 1 条记录

### Requirement: 不修改 AstrBot 原数据

profile_generator 插件 MUST NOT 读取、修改、或删除 AstrBot 自己的 conversations.content / platform_message_history 表。

#### Scenario: AstrBot 数据不受影响
- **WHEN** 插件捕获消息写入自有数据库
- **THEN** data_v4.db 中的 conversations / platform_message_history 表保持不变
