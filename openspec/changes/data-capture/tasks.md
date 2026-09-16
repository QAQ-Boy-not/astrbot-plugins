# Tasks: data-capture

## 1. Schema 实施

- [x] 1.1 在 `profile_pipeline/profile_generator/main.py` 里实现 4 张表的 CREATE TABLE（messages / attachments / mentions / quotes），启动时自动建表
- [x] 1.2 在同文件实现连接管理（`/AstrBot/data/profile_data.db` 路径，单例连接 + 索引创建）
- [x] 1.3 验证：把插件 zip 上传 AstrBot → 重载 → 用 sqlite_toolkit 检查 4 张表已建好，索引齐全

## 2. 消息解析逻辑

- [x] 2.1 实现 `_extract_message_chain(msg)` 函数，遍历 message_chain 按 component 类型分桶到 4 个列表
- [x] 2.2 实现 Plain 处理（text 拼成 content）
- [x] 2.3 实现 At 处理（user_id = comp.qq, name = comp.name）
- [x] 2.4 实现 Image / Video / File 处理（type + local_path + remote_url + file_name + size + mime_type + width/height）
- [x] 2.5 实现 Reply 处理（quoted_text + quoted_type，不存原消息 ID）
- [x] 2.6 实现 Face 处理（[表情:id] 文本占位）

## 3. 钩子集成

- [x] 3.1 实现 `@filter.event_message_type(EventMessageType.ALL)` 钩子，调用解析逻辑，写入 4 张表
- [x] 3.2 钩子里加 try-except，任何错误只打印不抛（不影响 bot 主流程）
- [x] 3.3 验证：发 4 种消息（普通/@/图片/引用） → sqlite_toolkit 查表 → 每张表都有对应数据

## 4. 验证与提交

- [x] 4.1 mock 测试 4 种消息类型，验证 extract_message_chain 输出正确
- [x] 4.2 git commit profile_pipeline/profile_generator/
- [ ] 4.3 在真实群里跑 30 分钟验证（需要 AstrBot 容器环境）
- [ ] 4.4 opsx:archive 归档本 change
