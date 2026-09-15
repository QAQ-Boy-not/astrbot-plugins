# profile_generator

AstrBot 插件，捕获群里所有消息到自有数据库。

## 功能

- 钩子 `@filter.event_message_type(EventMessageType.ALL)` 触发，捕获群里所有消息
- 不依赖 @bot——普通聊天也存
- 不修改 AstrBot 原数据（`conversations.content` 等不动）
- 4 张表 3NF schema（messages / attachments / mentions / quotes）

## 架构

```
profile_generator/
├── main.py                       # 插件入口：钩子 + extract_message
└── metadata.yaml

../shared/                        # 跨插件共享
├── db.py                         # 连接管理 + schema + 迁移
├── models.py                     # Message / Attachment / Mention / Quote dataclass
└── message_repository.py        # CRUD 封装
```

## 数据落点

```
/AstrBot/data/plugin_data/profile_generator/profile.db
```

放在 AstrBot 插件数据目录——覆盖 / 卸载时 AstrBot 会识别并询问。

**首次启动**：如果检测到旧位置 `/AstrBot/data/profile_data.db`（早期版本），自动迁移。

## 打包

```bash
python3 profile_pipeline/scripts/build.py \
    profile_pipeline/profile_generator \
    /home/wangjing/ai/astrbot/profile_generator.zip
```

build 脚本自动：
- 读当前版本号
- 跨天打包：自动加日期戳（同 `0.2.0-20260915`）
- 同一天打包：版本号不变
- 同步更新 `metadata.yaml` 和 `main.py` 的 `@register`
- 打包 zip（含 shared/ 子目录）
- 打印 git commit 提示

跳过版本号（调试用）：加 `--no-bump`。

## 当前版本

v0.2.0-20260915（首次日期戳版本）
