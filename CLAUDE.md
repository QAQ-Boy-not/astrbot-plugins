# CLAUDE.md

> 本文件给后续 Claude 会话用，记录仓库背景、目录结构、Git 工作流、版本规范。
> 插件细节看各自目录下的 CLAUDE.md。

---

## 1. 项目背景

AstrBot 插件仓库（纯本地，**无远端**）。当前包含：

| 插件 | 目录 | 状态 |
|------|------|------|
| **inspect_response** | `inspect_response/` | v2.0.0，调试用，4 点全链路打印 |
| **profile_generator** | `profile_pipeline/profile_generator/` | v0.2.0，Phase 1 数据捕获 |

旧插件 `info_extend` 已删除（功能被 AstrBot 内置 `identifier` 配置覆盖）。

OpenSpec 变更管理：`openspec/changes/`（进行中）、`openspec/specs/`（已归档）。
SQLite Skill：`tools/sqlite-toolkit/`（本地探查工具）。

---

## 2. 目录结构

```
info_extend/                           ← 仓库根
├── .git/                              ← 本地 git（无 remote）
├── .gitignore                         ← 排除 .claude/、*.zip、__pycache__/ 等
├── CLAUDE.md                          ← 本文件
├── inspect_response/                  ← 调试插件（v2.0.0）
│   ├── main.py
│   ├── metadata.yaml
│   └── README.md
├── profile_pipeline/                  ← 用户画像项目（3 阶段）
│   ├── profile_generator/             ← Phase 1: 数据捕获（v0.2.0）
│   │   ├── main.py
│   │   └── metadata.yaml
│   └── shared/                        ← 跨插件共享（Repository 层）
│       ├── __init__.py
│       ├── db.py
│       ├── models.py
│       └── message_repository.py
├── tools/                              ← 工具集
│   └── sqlite-toolkit/                ← 本地 SQLite 探查 Skill
│       ├── SKILL.md
│       └── scripts/toolkit.py
├── openspec/                           ← OpenSpec 变更管理
│   ├── config.yaml
│   ├── changes/                        ← 进行中的 change
│   └── specs/                          ← 已归档 spec
└── data_v4.db                          ← AstrBot 数据（临时下载，已删除）
```

**zips 在父目录**：
- `/home/wangjing/ai/astrbot/inspect_response.zip`
- `/home/wangjing/ai/astrbot/profile_generator.zip`

---

## 3. Git 工作流规范 ⚠️ 必读

> **本仓库只有本地 git，没有远端**——所有改动都靠本地 commit 留痕。
> 改之前先确认 working tree 是干净的。

### 3.1 一个 commit 只做一件事

```
❌ "fix bug and add new feature"
✅ "info_extend: 改为 append extra_user_content_parts"
✅ "profile_pipeline: 重构 - 引入 shared/ 模块"
```

### 3.2 commit message 格式

```
第一行（≤ 50 字）：<scope>: <动词> <对象>

空行

详细原因（可选）：解释为什么这么改、对比之前的设计、踩过的坑。
```

**scope 约定**：`inspect_response:` `profile_pipeline:` `tools:` `openspec:` 或仓库级 `repo:` `docs:`。

### 3.3 改之前先 `git status`

干净状态意味着可以放心做实验。改坏了 `git checkout -- .` 一键恢复。

### 3.4 不要 `git add .` 偷懒

```bash
git add profile_pipeline/shared/models.py  # 具体文件
git commit -m "..."
```

---

## 4. ⚠️ 版本号规范（SemVer）

**每个插件 zip 必须带正确的 version 字段**——这是 AstrBot 显示"已加载 vs 旧版本"的依据。

### 4.1 格式：`MAJOR.MINOR.PATCH`

```
MAJOR.MINOR.PATCH

例：0.2.0
```

### 4.2 何时该升

| 改动类型 | 升什么 | 例 |
|---------|--------|-----|
| 新增插件 | 0.1.0 | profile_generator v0.1.0 |
| 加新钩子/新字段（用户可见） | MINOR +1 | v0.1.0 → v0.2.0 |
| 加新表/新列（DB schema 变化） | MINOR +1 | v0.2.0 → v0.3.0 |
| 重构（不暴露给用户） | PATCH +1 或不升 | v0.2.0 → v0.2.1 |
| Bug fix | PATCH +1 | v0.2.0 → v0.2.1 |
| 删字段/改接口（破坏性） | MAJOR +1 | v0.2.0 → v1.0.0 |

### 4.3 同步两个地方

改版本号必须**同时改**：

1. `metadata.yaml` 里的 `version` 字段
2. `main.py` 里 `@register` 装饰器的第四个参数

```python
# metadata.yaml
version: 0.3.0

# main.py
@register("profile_generator", "anonymous", "...", "0.3.0")
```

**任何 commit 改代码 + 升版本号**——否则 AstrBot 看到的是旧版本。

---

## 5. 部署工作流

> ⚠️ **打包/上传/重载**都需要人确认。AI 不主动操作。

1. 本地改代码 → 升版本号 → 测试 → `git commit`
2. **打包**（用户说才打）：
   ```bash
   # 单插件
   cd profile_pipeline/profile_generator
   zip ../../profile_generator.zip main.py metadata.yaml -j

   # 多文件（带 shared/）
   cd profile_pipeline
   zip ../profile_generator.zip \
       profile_generator/main.py profile_generator/metadata.yaml \
       shared/__init__.py shared/db.py shared/models.py shared/message_repository.py
   ```
3. **上传**：Web UI → 插件管理 → 上传 zip
4. **重载**：Web UI → 重载按钮（**不重启容器**）
5. **验证**：`docker logs -f astrbot | grep 插件名`

---

## 6. 安全红线

- ❌ 不碰 AstrBot 数据库（`/AstrBot/data/data_v4.db`）
- ❌ 不 `rm -rf` 线上文件
- ❌ 不主动打包 zip
- ❌ 不决策性操作（部署/重载/清理数据）—— 等用户说

profile_generator 用自己的 DB（`/AstrBot/data/profile_data.db`），不污染 AstrBot 原数据。

---

## 7. 关键引用

- 持久记忆：`/home/wangjing/.claude/projects/-home-wangjing-ai-astrbot-info-extend/memory/`
  - `astrbot-provider-request-structure.md` — ProviderRequest 数据结构
  - `astrbot-openai-mapping.md` — 改哪里 → 影响哪里
  - `astrbot-plugin-dev-guide.md` — 踩坑经验、priority、日志规范
  - `astrbot-prompt-caching-warning.md` — prompt caching 红线
  - `astrbot-knowledge-base.md` — 内置知识库原理
  - `astrbot-v4-config-layers.md` — 全局 vs agent 专属 abconf_*.json
  - `astrbot-conversation-management.md` — Session/Conversation 管理
  - `astrbot-message-structure.md` — AstrBotMessage + message_chain 实战数据 + 4 表 schema
  - `profile-extraction-design-philosophy.md` — 画像项目设计哲学
  - `long-text-context-strategies.md` — 4 种长文本处理策略
  - `tool-mcp-skill-philosophy.md` — Tool/MCP/Skill 都是代码的不同包装

- OpenSpec 流程：explore → propose → apply → archive
- sqlite-toolkit 用法：`python3 tools/sqlite-toolkit/scripts/toolkit.py --db <PATH> <command>`
