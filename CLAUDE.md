# CLAUDE.md

> 本文件给后续 Claude 会话用，记录仓库背景、目录结构、Git 工作流规范。
> 插件细节看各自目录下的 CLAUDE.md。

---

## 1. 项目背景

AstrBot 插件仓库（纯本地，**无远端**）。包含两个独立插件：

| 插件 | 目录 | 用途 |
|------|------|------|
| **info_extend** | `info_extend/` | 静默向 `extra_user_content_parts` 注入用户消息上下文（User ID/Nickname/Group） |
| **inspect_response** | `inspect_response/` | 极简 JSON 调试插件，只打 2 次完整 JSON |

每个插件的细节、字段约束、调试记录，参考各自目录下的 `CLAUDE.md`。

---

## 2. 目录结构

```
info_extend/                       ← 仓库根
├── .git/                          ← 本地 git（无 remote）
├── .gitignore                     ← 排除 .claude/、*.zip、__pycache__/ 等
├── CLAUDE.md                      ← 本文件
├── info_extend/                   ← 插件 1
│   ├── main.py
│   ├── metadata.yaml
│   ├── README.md
│   └── CLAUDE.md                  ← 插件 1 专属文档
└── inspect_response/              ← 插件 2
    ├── main.py
    ├── metadata.yaml
    ├── README.md
    └── CLAUDE.md                  ← 插件 2 专属文档
```

**zips 在父目录**：`/home/wangjing/ai/astrbot/info_extend.zip` 和 `/home/wangjing/ai/astrbot/inspect_response.zip`（不在仓库内）。

---

## 3. Git 工作流规范 ⚠️ 必读

> **本仓库只有本地 git，没有远端**——所有改动都靠本地 commit 留痕。
> 改之前先确认 working tree 是干净的。

### 3.1 一个 commit 只做一件事

把"加新功能"和"修 bug"分两次 commit。混在一起的 commit 后期难以回退、cherry-pick、review。

```
❌ "fix bug and add new feature"
✅ "info_extend: 改为 append extra_user_content_parts"
✅ "info_extend: 修复群聊名称解析兜底逻辑"
```

### 3.2 commit message 格式

```
第一行（≤ 50 字）：<scope>: <动词> <对象>
  例：info_extend: 改为 append extra_user_content_parts

空行

详细原因（可选）：解释为什么这么改、对比之前的设计、踩过的坑。
```

**scope 约定**：插件名（`info_extend:` `inspect_response:`），或仓库级改动用 `repo:` 或 `docs:`。

### 3.3 改之前先 `git status`

干净状态（`nothing to commit, working tree clean`）意味着：
- 没有未保存的改动
- 可以放心做实验（改坏了 `git checkout -- .` 一键恢复）
- 不会出现"咦这是上次的改动还是这次的"

### 3.4 不要 `git add .` 偷懒

养成 `git add <specific-file>` 的习惯：

```bash
git add info_extend/main.py
git commit -m "info_extend: ..."
```

为什么：避免误提交临时文件、调试 print、不该进的配置。`git status` 和 `git diff --staged` 先看清楚再 add。

---

## 4. 部署工作流

> ⚠️ **打包/上传/重载**都需要人确认。AI 不主动操作。

1. 本地改代码 → 测试 → `git commit`
2. **打包**（用户说才打）：
   ```bash
   cd info_extend/  # 或 inspect_response/
   zip ../info_extend.zip main.py metadata.yaml README.md CLAUDE.md -j
   ```
3. **上传**：Web UI → 插件管理 → 上传 zip
4. **重载**：Web UI → 重载按钮（**不重启容器**）
5. **验证**：`docker logs -f astrbot | grep 插件名`

---

## 5. 关键引用

- 持久记忆：`/home/wangjing/.claude/projects/-home-wangjing-ai-astrbot-info-extend/memory/`
  - `astrbot-provider-request-structure.md` — ProviderRequest 数据结构
  - `astrbot-openai-mapping.md` — 改哪里 → 影响哪里
  - `astrbot-plugin-dev-guide.md` — 踩坑经验、priority、日志规范
  - `astrbot-prompt-caching-warning.md` — prompt caching 红线
  - `astrbot-knowledge-base.md` — 内置知识库原理

---

## 6. 安全红线

- ❌ 不碰 AstrBot 数据库（`/AstrBot/data/astrbot_bot.db`）
- ❌ 不 `rm -rf` 线上文件
- ❌ 不主动打包 zip
- ❌ 不决策性操作（部署/重载/清理数据）—— 等用户说