"""SQLite 只读探查工具。所有函数必须显式传入 db_path。"""

import sqlite3
import json
import csv
import sys
from pathlib import Path


def find_db(db_path: str) -> Path:
    """必须显式传路径。"""
    p = Path(db_path).expanduser().resolve()
    if not p.exists():
        raise FileNotFoundError(f"DB 文件不存在: {p}")
    return p


def db_info(db_path: str) -> dict:
    """DB 元信息：路径、大小、版本、表/索引数等。"""
    p = find_db(db_path)
    stat = p.stat()
    with sqlite3.connect(p) as conn:
        return {
            "path": str(p),
            "size_bytes": stat.st_size,
            "size_human": _human_size(stat.st_size),
            "sqlite_version": sqlite3.sqlite_version,
            "journal_mode": conn.execute("PRAGMA journal_mode").fetchone()[0],
            "tables": conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'").fetchone()[0],
            "indexes": conn.execute("SELECT COUNT(*) FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%'").fetchone()[0],
        }


def _human_size(n: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def list_tables(db_path: str) -> list[str]:
    """列出所有表名。"""
    with sqlite3.connect(find_db(db_path)) as conn:
        return [r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' ORDER BY name"
        ).fetchall()]


def get_schema(table: str, db_path: str) -> str:
    """返回 CREATE TABLE 语句。"""
    with sqlite3.connect(find_db(db_path)) as conn:
        row = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name=? AND type='table'", (table,)
        ).fetchone()
    if not row:
        raise ValueError(f"表不存在: {table}")
    return row[0]


def all_schemas(db_path: str) -> str:
    """所有表的 CREATE 语句拼起来。"""
    with sqlite3.connect(find_db(db_path)) as conn:
        rows = conn.execute(
            "SELECT sql FROM sqlite_master WHERE sql IS NOT NULL AND name NOT LIKE 'sqlite_%' ORDER BY type, name"
        ).fetchall()
    return "\n;\n\n".join(r[0] for r in rows if r[0]) + ";"


def table_info(table: str, db_path: str) -> list[dict]:
    """列的元信息。"""
    with sqlite3.connect(find_db(db_path)) as conn:
        rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return [
        {"name": r[1], "type": r[2], "notnull": bool(r[3]), "default": r[4], "pk": bool(r[5])}
        for r in rows
    ]


def preview_table(table: str, db_path: str, limit: int = 3):
    """返回 (列名列表, 行列表)。"""
    with sqlite3.connect(find_db(db_path)) as conn:
        cols = [d[0] for d in conn.execute(f"SELECT * FROM {table} LIMIT 1").description]
        rows = conn.execute(f"SELECT * FROM {table} LIMIT {limit}").fetchall()
    return cols, rows


def summary(db_path: str) -> list[dict]:
    """每张表的行数、列数、索引数。"""
    with sqlite3.connect(find_db(db_path)) as conn:
        tables = list_tables(db_path)
        result = []
        for t in tables:
            result.append({
                "table": t,
                "rows": conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0],
                "cols": len(conn.execute(f"PRAGMA table_info({t})").fetchall()),
                "indexes": len(conn.execute(f"PRAGMA index_list({t})").fetchall()),
            })
    return sorted(result, key=lambda x: -x["rows"])


def query(sql: str, db_path: str, params: tuple = ()):
    """执行 SELECT/WITH。返回 (列名, 行)。"""
    sql_clean = sql.strip().rstrip(";")
    upper = sql_clean.upper()
    if not (upper.startswith("SELECT") or upper.startswith("WITH")):
        raise ValueError("只支持 SELECT/WITH")
    with sqlite3.connect(find_db(db_path)) as conn:
        cur = conn.execute(sql, params)
        cols = [d[0] for d in cur.description] if cur.description else []
        return cols, cur.fetchall()


def search(text: str, db_path: str, limit_per_table: int = 5) -> list[dict]:
    """跨所有 TEXT/JSON 列 LIKE 搜索。"""
    pattern = f"%{text}%"
    results = []
    with sqlite3.connect(find_db(db_path)) as conn:
        for table in list_tables(db_path):
            cols_info = conn.execute(f"PRAGMA table_info({table})").fetchall()
            text_cols = [c[1] for c in cols_info
                         if any(t in c[2].upper() for t in ["TEXT", "JSON", "CHAR"])
                         or c[2] == ""]
            for col in text_cols:
                try:
                    rows = conn.execute(
                        f"SELECT * FROM {table} WHERE CAST({col} AS TEXT) LIKE ? LIMIT ?",
                        (pattern, limit_per_table),
                    ).fetchall()
                    if rows:
                        results.append({"table": table, "column": col, "rows": rows})
                except sqlite3.Error:
                    continue
    return results


def _json_contains(obj, text: str) -> bool:
    """递归搜索 JSON 结构中的字符串。"""
    if isinstance(obj, str):
        return text in obj
    if isinstance(obj, dict):
        return any(_json_contains(v, text) for v in obj.values())
    if isinstance(obj, list):
        return any(_json_contains(v, text) for v in obj)
    return False


def search_json(
    text: str,
    db_path: str,
    table: str | None = None,
    columns: list[str] | None = None,
    limit: int = 5,
) -> list[dict]:
    """递归搜索 JSON 列内的字符串。

    Args:
        text: 要搜的字符串
        db_path: DB 路径
        table: 表名（None = 所有表）
        columns: JSON 列名列表（None = 自动找所有 JSON 列）
        limit: 每列返回行数上限

    Returns:
        [{table, column, rowid, data}]
    """
    results = []
    with sqlite3.connect(find_db(db_path)) as conn:
        tables = [table] if table else list_tables(db_path)
        for t in tables:
            cols_info = conn.execute(f"PRAGMA table_info({t})").fetchall()
            json_cols = columns if columns else [
                c[1] for c in cols_info if "JSON" in c[2].upper()
            ]
            for col in json_cols:
                try:
                    rows = conn.execute(
                        f"SELECT rowid, {col} FROM {t}"
                    ).fetchall()
                except sqlite3.Error:
                    continue
                count = 0
                for rowid, json_str in rows:
                    if not json_str:
                        continue
                    try:
                        data = json.loads(json_str)
                    except (json.JSONDecodeError, TypeError):
                        continue
                    if _json_contains(data, text):
                        results.append({
                            "table": t,
                            "column": col,
                            "rowid": rowid,
                            "data": data,
                        })
                        count += 1
                        if count >= limit:
                            break
    return results


def export_query(sql: str, output_path: str, db_path: str, fmt: str = "json") -> int:
    """导出查询结果到 JSON/CSV。返回行数。"""
    cols, rows = query(sql, db_path)
    if fmt == "json":
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(
                [dict(zip(cols, [str(v) if v is not None else None for v in r])) for r in rows],
                f, ensure_ascii=False, indent=2,
            )
    elif fmt == "csv":
        with open(output_path, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f)
            w.writerow(cols)
            w.writerows(rows)
    else:
        raise ValueError(f"不支持的格式: {fmt}")
    return len(rows)


def format_table(headers: list[str], rows: list[tuple], max_width: int = 50) -> str:
    """格式化为文本表格。"""
    if not rows:
        return "(空)"
    str_rows = [[str(v)[:max_width] if v is not None else "NULL" for v in r] for r in rows]
    widths = [min(max(len(h), max((len(c[i]) for c in str_rows), default=0)), max_width)
              for i, h in enumerate(headers)]
    line = lambda cells: " | ".join(c.ljust(widths[i]) for i, c in enumerate(cells))
    lines = [line(headers), "-+-".join("-" * w for w in widths)]
    lines.extend(line(r) for r in str_rows)
    return "\n".join(lines)


# ============== CLI ==============

def main():
    import argparse
    p = argparse.ArgumentParser(description="SQLite 只读探查工具（必须 --db 指定路径）")
    p.add_argument("--db", required=True, help="DB 文件路径")
    sub = p.add_subparsers(dest="cmd", required=True)

    sub.add_parser("tables")
    sub.add_parser("info")
    sub.add_parser("summary")
    sub.add_parser("schema-all")

    s1 = sub.add_parser("schema"); s1.add_argument("table")
    s2 = sub.add_parser("preview"); s2.add_argument("table"); s2.add_argument("--limit", type=int, default=3)
    s3 = sub.add_parser("query"); s3.add_argument("sql")
    s4 = sub.add_parser("search"); s4.add_argument("text"); s4.add_argument("--limit", type=int, default=5)
    s6 = sub.add_parser("search-json"); s6.add_argument("text"); s6.add_argument("--table"); s6.add_argument("--limit", type=int, default=5)
    s5 = sub.add_parser("export"); s5.add_argument("sql"); s5.add_argument("output"); s5.add_argument("--fmt", choices=["json","csv"], default="json")

    args = p.parse_args()

    try:
        if args.cmd == "tables":
            for t in list_tables(args.db):
                print(t)
        elif args.cmd == "info":
            for k, v in db_info(args.db).items():
                print(f"{k}: {v}")
        elif args.cmd == "summary":
            data = summary(args.db)
            print(format_table(["table", "rows", "cols", "indexes"],
                               [(r["table"], r["rows"], r["cols"], r["indexes"]) for r in data]))
        elif args.cmd == "schema-all":
            print(all_schemas(args.db))
        elif args.cmd == "schema":
            print(get_schema(args.table, args.db))
        elif args.cmd == "preview":
            cols, rows = preview_table(args.table, args.db, args.limit)
            print(format_table(cols, rows))
        elif args.cmd == "query":
            cols, rows = query(args.sql, args.db)
            print(format_table(cols, rows))
        elif args.cmd == "search":
            results = search(args.text, args.db, args.limit)
            if not results:
                print(f"未找到 '{args.text}'")
            else:
                for r in results:
                    print(f"\n[{r['table']}.{r['column']}]")
                    print(format_table([f"col{i}" for i in range(len(r["rows"][0]))], r["rows"]))
        elif args.cmd == "search-json":
            results = search_json(args.text, args.db, args.table, limit=args.limit)
            if not results:
                print(f"未在 JSON 中找到 '{args.text}'")
            else:
                for r in results:
                    print(f"\n[{r['table']}.{r['column']} rowid={r['rowid']}]")
                    print(json.dumps(r["data"], ensure_ascii=False, indent=2)[:500])
        elif args.cmd == "export":
            n = export_query(args.sql, args.output, args.db, args.fmt)
            print(f"✓ {n} 行 → {args.output}")
    except Exception as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
