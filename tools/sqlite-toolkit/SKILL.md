---
name: sqlite-toolkit
description: 只读 SQLite 数据库探查（AI 工具）。列出表、看 schema、预览数据、执行 SELECT、递归搜索 JSON。必须显式传 db_path。
---

# sqlite-toolkit

## 何时使用

AI/LLM 需要读取 SQLite 数据库（`.db` / `.sqlite` / `.sqlite3`）的结构或数据，用于分析、调试、回答问题时使用。

## CLI

```bash
python3 tools/sqlite-toolkit/scripts/toolkit.py --db <DB_PATH> <command> [args]
```

| command | 作用 |
|---------|------|
| `tables` | 列出所有表 |
| `info` | DB 元信息 |
| `summary` | 各表行数+列数+索引数 |
| `schema <table>` | 单表 CREATE 语句 |
| `schema-all` | 全部 CREATE 语句 |
| `preview <table> [--limit N]` | 预览前 N 行（默认 3） |
| `query "<SQL>"` | 执行 SELECT/WITH |
| `search "<text>"` | 跨 TEXT/JSON 列 LIKE 搜索 |
| `search-json "<text>" [--table T]` | 递归搜索 JSON 嵌套字符串 |
| `export "<SQL>" <out> [--fmt json\|csv]` | 导出结果 |

## 约束

- 只读，不修改 DB
- `query()` 只接受 `SELECT` / `WITH` 开头
- 所有函数第一个位置参数是 `db_path`