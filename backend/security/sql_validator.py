from __future__ import annotations

from typing import Any

import sqlglot
from sqlglot import exp

from config import MAX_RESULT_ROWS

DANGEROUS_NODES = [
    getattr(exp, name)
    for name in (
        "Insert",
        "Update",
        "Delete",
        "Drop",
        "Create",
        "Alter",
        "TruncateTable",
        "Merge",
        "Grant",
        "Revoke",
        "Command",
        "Transaction",
        "Commit",
        "Rollback",
        "Attach",
        "Detach",
        "Pragma",
        "Set",
        "Use",
        "Copy",
    )
    if hasattr(exp, name)
]

DANGEROUS_FUNCTIONS = {
    "read_csv",
    "read_csv_auto",
    "read_parquet",
    "read_json",
    "read_json_auto",
    "glob",
    "sniff_csv",
    "load",
    "install",
    "shell",
    "system",
    "exec",
    "xp_cmdshell",
}


def validate_sql(
    sql: str,
    allowed_tables: list[str] | None = None,
    dialect: str = "duckdb",
    max_rows: int = MAX_RESULT_ROWS,
) -> dict[str, Any]:
    issues: list[str] = []
    cleaned = (sql or "").strip().rstrip(";")
    if not cleaned:
        return {"valid": False, "safe_sql": "", "issues": ["SQL 不能为空"]}

    try:
        statements = sqlglot.parse(cleaned, read=dialect)
    except Exception as exc:
        return {"valid": False, "safe_sql": "", "issues": [f"SQL 语法解析失败：{exc}"]}

    if len(statements) != 1:
        return {"valid": False, "safe_sql": "", "issues": ["不允许一次执行多条 SQL 语句"]}

    tree = statements[0]
    if not isinstance(tree, exp.Query):
        return {"valid": False, "safe_sql": "", "issues": ["只允许 SELECT 查询语句"]}

    for node in tree.walk():
        if isinstance(node, tuple(DANGEROUS_NODES)):
            issues.append(f"包含危险操作：{node.key}")
        if isinstance(node, exp.Into):
            issues.append("不允许使用 SELECT INTO")
        if isinstance(node, exp.Anonymous) and str(node.name).lower() in DANGEROUS_FUNCTIONS:
            issues.append(f"不允许调用敏感函数：{node.name}")

    allowed = {str(table).lower() for table in (allowed_tables or [])}
    for table in tree.find_all(exp.Table):
        name = table.name
        if not name:
            continue
        lowered = name.lower()
        if lowered.startswith("sqlite_") or lowered in ("information_schema", "pg_catalog"):
            issues.append(f"不允许访问系统表：{name}")
            continue
        if allowed and lowered not in allowed:
            issues.append(f"表 {name} 不在授权范围内")

    if issues:
        return {"valid": False, "safe_sql": "", "issues": issues}

    safe_sql = cleaned
    limit_node = tree.find(exp.Limit)
    if limit_node is None:
        safe_sql = tree.limit(max_rows).sql(dialect=dialect)
    else:
        try:
            limit_value = int(limit_node.expression.this)
            if limit_value > max_rows:
                safe_sql = f"SELECT * FROM ({cleaned}) AS _limited_rows LIMIT {max_rows}"
        except Exception:
            safe_sql = f"SELECT * FROM ({cleaned}) AS _limited_rows LIMIT {max_rows}"

    return {"valid": True, "safe_sql": safe_sql, "issues": []}
