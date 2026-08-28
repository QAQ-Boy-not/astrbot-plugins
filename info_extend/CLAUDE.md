# CLAUDE.md

> 本文件给后续 Claude 会话用，记录项目背景、关键路径、约定。
> 修改本文件时同步更新。

---

## 1. 项目背景

**info_extend** 是 AstrBot 插件，功能是：把机器人收到的用户消息格式化为「用户xx对你说xx」后，追加到 `system_prompt` 末尾送给大模型。

**核心原则**（基于 astrbot/core/provider/entities.py 源码）：

| 字段 | 真实类型 | 是否可改 |
|------|---------|---------|
| `req.contexts` | `list[dict]` OpenAI 格式消息数组 | ❌ 绝不动（破坏多模态/tool call） |
| `req.conversation` | `Conversation` 会话对象（非消息列表） | ❌ 绝不动 |
| `req.system_prompt` | `str` | ✅ **唯一安全的修改点** |
| `req.prompt` | `str` 用户原始消息 | ❌ 不动 |
| `req.image_urls` | `list[str]` | ❌ 不动 |
| `req.extra_user_content_parts` | `list[ContentPart]` | ❌ 不动 |

**历史踩坑**：曾经尝试改 `last_msg.content = [TextPart(...)]`，导致大模型直接挂。原因是 content 可能是 list[part]（多模态），整体替换丢图片/附件/工具调用。

---

## 2. 部署环境

### 主机 vs Docker 容器路径映射

| 用途 | 主机路径（公司服务器） | 容器内路径 |
|------|---------------------|-----------|
| AstrBot 配置 | `./config/...` | `/AstrBot/config/` |
| **插件目录** | `./data/plugins/info_extend/` | `/AstrBot/data/plugins/info_extend/` |
| 数据/数据库 | `./data/` | `/AstrBot/data/` |
| 日志 | `./data/logs/` | `/AstrBot/data/logs/` |

具体映射方式由 `docker-compose.yml` 的 `volumes` 段决定（典型写法 `./data:/AstrBot/data`）。

### 部署工作流

1. **本地开发**：在本机 `/home/wangjing/ai/astrbot/info_extend/` 修改 `main.py`
2. **同步**：通过 `scp` / `rsync` 推到公司服务器 `~/astrbot/data/plugins/info_extend/`
3. **热重载**：在 AstrBot Web UI 插件管理页面点「重载」按钮（**不要重启 Docker 容器**）
4. **打包**：除非用户明确说「打包」，否则不主动打 zip

### 备选：Web UI 上传

- 在 Web UI 插件管理页面点「上传」，选择本地 zip 文件
- zip 顶层结构必须是 `main.py` + `metadata.yaml` + 其他附属文件
- 上传后点「重载」

---

## 3. 关键代码约束

### main.py 必须遵守

```python
# ✅ 允许
req.system_prompt = original + "\n\n[当前消息] 用户X对你说：Y"

# ❌ 禁止（会炸）
req.contexts[-1]['content'] = something  # 破坏多模态结构
req.conversation = something              # 破坏会话持久化
last_msg.content = [TextPart(...)]        # 历史踩坑，强转类型
```

### 日志规范

- **必须用双通道**：`print()` + `logger.info()`（print 保证 docker logs 一定能看到）
- 每个 step 用 `try-except`，单点失败不中断整体
- 不依赖 `TextPart` 等可能不存在的导入——全部 `try-import` 兜底

### 加载失败的诊断流程

1. `docker logs -f astrbot` 看 `print` 输出
2. AstrBot Web UI → 日志面板看 `logger.info` 输出
3. 都看不到 → 插件根本没加载 → 检查 `metadata.yaml` 的 `name` 字段是否冲突

---

## 4. 文件清单

```
info_extend/
├── main.py            # 插件主体（on_llm_request 钩子）
├── metadata.yaml      # 插件元数据（name/display_name/desc/version/author/repo）
├── README.md          # 给用户看的说明（可为空）
├── CLAUDE.md          # 本文件，给 Claude 看
└── workflow-summary.md # 给领导看的工作流文档
```

### metadata.yaml 关键字段

```yaml
name: info_extend           # 必须唯一，Web UI 标识用
display_name: info_extend   # 展示名
desc: 把机器人接收到的消息格式化为"用户xx对你说xx"后发送给大模型
version: v1.0.0
author: your_name
repo: https://github.com/your/repo
```

`name` 改了之后必须删除老的同名插件，否则加载冲突。

---

## 5. AstrBot 源码参考

本地若没有 AstrBot 源码，调试时拉 master 分支：

```bash
# ProviderRequest 定义（req 各字段权威定义）
curl -s https://raw.githubusercontent.com/AstrBotDevs/AstrBot/master/astrbot/core/provider/entities.py

# Conversation 定义（req.conversation 的类型定义）
curl -s https://raw.githubusercontent.com/AstrBotDevs/AstrBot/master/astrbot/core/db/po.py
curl -s https://raw.githubusercontent.com/AstrBotDevs/AstrBot/master/astrbot/core/conversation_mgr.py
```

**注意**：`is_checkpoint_message(ctx)` 用于判定 contexts 里哪些是检查点消息（应当跳过），定义在 `astrbot/core/agent/message.py`。

---

## 6. 调试记录（追加式维护）

### v1.0.0 — 2026-08-27

- 错误：`TypeError: object of type 'Conversation' has no len()`
- 原因：把 `req.conversation` 当成消息列表用 `len()`
- 修复：识别 `Conversation` 是会话对象，改用 `req.contexts` 读消息列表
- 教训：**动手前先看权威源码，不要相信第三方 AI 索引**

### v1.0.1 — 2026-08-27

- 错误：强行修改 `last_msg.content = [TextPart(...)]` 导致大模型挂掉
- 原因：content 可能是 list[part]（多模态），整体替换丢图片/工具调用
- 修复：完全不动 contexts，只在 `system_prompt` 末尾追加用户标识
- 教训：**结构化字段宁可不碰，最稳的方案是用 system_prompt 传信息**

### v1.0.2 — 2026-08-27

- 错误：docker 中看不到任何插件日志
- 原因：插件加载在 `req.conversation` 处抛 TypeError，整个钩子中断，print 一行没执行
- 修复：双通道日志 `print + logger`，每个 step try-except
- 教训：**日志看不到 ≠ 插件没加载，可能是钩子中途挂了**