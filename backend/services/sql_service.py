from __future__ import annotations

import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from typing import Any

from agent.llm import llm_client
from agent.prompts import SQL_SYSTEM, SQL_USER
from config import MAX_RESULT_ROWS, QUERY_TIMEOUT
from models import DatabaseConnection, Dataset
from services import csv_service
from services.database_service import database_service
from services.schema_service import schema_prompt
from utils.data import _convert, quote_ident

CN_NUMBERS = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
NUMERIC_TYPES = ("int", "float", "double", "decimal", "real", "numeric", "bigint", "smallint")
TIME_KEYWORDS = ("date", "time", "日期", "时间", "月份", "month")
DIMENSION_KEYWORDS = ("商品名称", "商品类别", "产品", "商品", "类别", "分类", "地区", "区域", "城市", "客户", "部门", "渠道")


def _table_and_columns(schema: dict[str, Any], question: str = "") -> tuple[str, list[dict[str, Any]]]:
    if "tables" in schema:
        tables = schema.get("tables") or []
        if not tables:
            raise ValueError("数据库中没有可用的表")
        lowered = question.lower()
        chosen = next((table for table in tables if table["name"].lower() in lowered), tables[0])
        return chosen["name"], chosen["columns"]
    return schema["table_name"], schema["columns"]


def _is_numeric(column: dict[str, Any]) -> bool:
    return any(token in str(column.get("dtype", "")).lower() for token in NUMERIC_TYPES)


def _is_time(column: dict[str, Any]) -> bool:
    name = str(column.get("name", "")).lower()
    dtype = str(column.get("dtype", "")).lower()
    return any(token in dtype for token in ("date", "time")) or any(
        token in name for token in TIME_KEYWORDS
    )


def _find_column(columns: list[dict[str, Any]], question: str) -> dict[str, Any] | None:
    lowered = question.lower()
    matches = [column for column in columns if str(column["name"]).lower() in lowered]
    if not matches:
        return None
    return max(matches, key=lambda column: len(str(column["name"])))


def _metric_expression(columns: list[dict[str, Any]], question: str) -> tuple[str, str]:
    lowered = question.lower()
    names = {str(column["name"]): column for column in columns}
    numeric = [column for column in columns if _is_numeric(column)]

    for name, column in names.items():
        if name.lower() in lowered and _is_numeric(column):
            return quote_ident(name), name

    if any(token in lowered for token in ("销售额", "营收", "成交额", "销售金额")) and "销售额" not in names:
        if "单价" in names and "数量" in names:
            return f"{quote_ident('单价')} * {quote_ident('数量')}", "销售额"
    if any(token in lowered for token in ("销售额", "营收", "成交额")) and "销售额" in names:
        return quote_ident("销售额"), "销售额"

    preferred = ["销售额", "销售金额", "金额", "amount", "sales", "revenue", "利润", "price", "单价", "数量", "quantity"]
    for keyword in preferred:
        for name, column in names.items():
            if keyword.lower() in name.lower() and _is_numeric(column):
                return quote_ident(name), name

    if numeric:
        name = str(numeric[0]["name"])
        return quote_ident(name), name
    return "COUNT(*)", "记录数"


def _dimension_column(columns: list[dict[str, Any]], question: str) -> dict[str, Any] | None:
    explicit = _find_column(columns, question)
    if explicit and not _is_numeric(explicit):
        return explicit

    for keyword in DIMENSION_KEYWORDS:
        for column in columns:
            if keyword.lower() in str(column["name"]).lower() and not _is_numeric(column):
                return column
    for column in columns:
        if not _is_numeric(column) and not _is_time(column):
            return column
    return None


def _limit_number(question: str, default: int = 100) -> int:
    match = re.search(r"(?:前|top|最高的|最低的)\s*(\d+)\s*(?:个|名|款|种|条)?", question, re.IGNORECASE)
    if match:
        return max(1, min(int(match.group(1)), MAX_RESULT_ROWS))
    match = re.search(r"(?:前|top|最高的|最低的)\s*([一二两三四五六七八九十]+)\s*(?:个|名|款|种|条)?", question)
    if match:
        return CN_NUMBERS.get(match.group(1), default)
    return default


def _time_condition(columns: list[dict[str, Any]], question: str) -> tuple[str, str | None]:
    time_column = next((column for column in columns if _is_time(column)), None)
    if not time_column:
        return "", None

    quoted = quote_ident(str(time_column["name"]))
    match = re.search(r"最近\s*([一二两三四五六七八九十\d]+)\s*(天|日|周|个月|月|年)", question)
    if match:
        raw = match.group(1)
        number = int(raw) if raw.isdigit() else CN_NUMBERS.get(raw, 1)
        unit = match.group(2)
        unit_sql = {"天": "day", "日": "day", "周": "week", "个月": "month", "月": "month", "年": "year"}[unit]
        return f"{quoted} >= CURRENT_DATE - INTERVAL '{number} {unit_sql}'", "month"

    match = re.search(r"最近\s*(\d+)\s*个?月", question)
    if match:
        return f"{quoted} >= CURRENT_DATE - INTERVAL '{int(match.group(1))} month'", "month"

    if "今年" in question:
        return f"EXTRACT(YEAR FROM {quoted}) = EXTRACT(YEAR FROM CURRENT_DATE)", "month"
    if "上个月" in question:
        return f"DATE_TRUNC('month', {quoted}) = DATE_TRUNC('month', CURRENT_DATE - INTERVAL '1 month')", "month"
    if "本月" in question:
        return f"DATE_TRUNC('month', {quoted}) = DATE_TRUNC('month', CURRENT_DATE)", "month"
    return "", "month"


def heuristic_sql(question: str, schema: dict[str, Any]) -> dict[str, Any]:
    question = question.replace("分类", "类别")
    table, columns = _table_and_columns(schema, question)
    table_sql = quote_ident(table)
    lowered = question.lower()

    time_column = next((column for column in columns if _is_time(column)), None)
    dimension = _dimension_column(columns, question)
    metric_sql, metric_name = _metric_expression(columns, question)

    where_sql, _ = _time_condition(columns, question)
    where = f" WHERE {where_sql}" if where_sql else ""

    wants_count = any(token in question for token in ("多少条", "几条", "记录数", "订单数", "数量有多少", "计数", "count"))
    wants_avg = any(token in question for token in ("平均", "均值", "人均"))
    wants_max = any(token in question for token in ("最大", "最高")) and not any(
        token in question for token in ("最高", "排名", "前")
    )
    wants_min = any(token in question for token in ("最小", "最低"))
    group_intent = any(
        token in question for token in ("每个", "各", "按", "分组", "分别", "排名", "最高", "最低", "前", "top", "分布", "占比")
    )
    trend_intent = any(token in question for token in ("趋势", "每月", "按月", "月度", "按年", "每年", "每天", "按日", "走势"))

    if wants_count and ("订单数" in question or "记录数" in question or "多少条" in question):
        if dimension and group_intent:
            sql = (
                f"SELECT {quote_ident(str(dimension['name']))} AS \"维度\", COUNT(*) AS \"记录数\" "
                f"FROM {table_sql}{where} GROUP BY 1 ORDER BY \"记录数\" DESC LIMIT {_limit_number(question, 20)}"
            )
            return {"sql": sql, "explanation": "统计各维度的记录数量", "chart_type": "bar"}
        sql = f"SELECT COUNT(*) AS \"记录数\" FROM {table_sql}{where}"
        return {"sql": sql, "explanation": "统计符合条件的记录数量", "chart_type": "table"}

    if trend_intent and time_column:
        grain = "year" if any(token in question for token in ("按年", "每年", "年度")) else "day" if any(
            token in question for token in ("每天", "按日", "每日")
        ) else "month"
        alias = {"year": "年份", "month": "月份", "day": "日期"}[grain]
        aggregate = "AVG" if wants_avg else "SUM"
        sql = (
            f"SELECT DATE_TRUNC('{grain}', {quote_ident(str(time_column['name']))}) AS \"{alias}\", "
            f'{aggregate}({metric_sql}) AS "{metric_name}" FROM {table_sql}{where} '
            f'GROUP BY 1 ORDER BY 1 LIMIT {MAX_RESULT_ROWS}'
        )
        return {"sql": sql, "explanation": f"按{alias}汇总趋势", "chart_type": "line"}

    if group_intent and dimension:
        aggregate = "AVG" if wants_avg else "MAX" if wants_max else "MIN" if wants_min else "SUM"
        order = "ASC" if wants_min else "DESC"
        sql = (
            f"SELECT {quote_ident(str(dimension['name']))} AS \"维度\", {aggregate}({metric_sql}) AS \"{metric_name}\" "
            f"FROM {table_sql}{where} GROUP BY 1 ORDER BY \"{metric_name}\" {order} "
            f"LIMIT {_limit_number(question, 20)}"
        )
        return {"sql": sql, "explanation": f"按{dimension['name']}汇总{metric_name}", "chart_type": "bar"}

    if any(token in question for token in ("总计", "合计", "总和", "总额", "平均", "最大", "最小")):
        aggregate = "AVG" if wants_avg else "MAX" if wants_max else "MIN" if wants_min else "SUM"
        sql = f'SELECT {aggregate}({metric_sql}) AS "{metric_name}" FROM {table_sql}{where}'
        return {"sql": sql, "explanation": f"计算{metric_name}的整体汇总", "chart_type": "table"}

    sql = f"SELECT * FROM {table_sql}{where} LIMIT 20"
    return {"sql": sql, "explanation": "返回数据集样例记录", "chart_type": "table"}


def generate_sql(
    question: str, schema: dict[str, Any], history: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    history_text = "\n".join(
        f"{item['role']}：{item['content'][:200]}" for item in (history or [])[-6:]
    )
    result = llm_client.chat_json(
        SQL_SYSTEM,
        SQL_USER.format(schema=schema_prompt(schema), history=history_text or "无", question=question),
    )
    if result and result.get("sql"):
        return {
            "sql": str(result["sql"]).strip(),
            "explanation": str(result.get("explanation") or "由大模型生成查询语句"),
            "chart_type": str(result.get("chart_type") or "bar"),
            "llm_used": True,
        }

    fallback = heuristic_sql(question, schema)
    fallback["llm_used"] = False
    return fallback


def repair_sql(
    question: str, schema: dict[str, Any], sql: str, error: str
) -> dict[str, Any]:
    from agent.prompts import REPAIR_SYSTEM, REPAIR_USER

    result = llm_client.chat_json(
        REPAIR_SYSTEM,
        REPAIR_USER.format(schema=schema_prompt(schema), question=question, sql=sql, error=error),
    )
    if result and result.get("sql"):
        return {
            "sql": str(result["sql"]).strip(),
            "explanation": str(result.get("explanation") or "已自动修复 SQL"),
            "chart_type": str(result.get("chart_type") or "bar"),
            "llm_used": True,
        }
    fallback = heuristic_sql(question, schema)
    fallback["llm_used"] = False
    fallback["explanation"] = "规则引擎重新生成查询语句"
    return fallback


def _normalize_rows(cursor) -> tuple[list[str], list[dict]]:
    columns = [column[0] for column in cursor.description]
    raw_rows = cursor.fetchmany(MAX_RESULT_ROWS + 1)
    rows = []
    for raw in raw_rows[:MAX_RESULT_ROWS]:
        rows.append({columns[index]: _convert(value) for index, value in enumerate(raw)})
    return columns, rows


def execute_sql(
    sql: str,
    dataset: Dataset | None = None,
    connection: DatabaseConnection | None = None,
) -> dict[str, Any]:
    if dataset is None and connection is None:
        raise ValueError("缺少数据集或数据库连接")

    started = time.perf_counter()

    if dataset is not None:
        conn = csv_service.connect()
        future = None
        executor = ThreadPoolExecutor(max_workers=1)
        try:
            future = executor.submit(lambda: _run_duckdb(conn, sql))
            columns, rows = future.result(timeout=QUERY_TIMEOUT)
        except FuturesTimeout as exc:
            try:
                conn.interrupt()
            except Exception:
                pass
            raise ValueError(f"查询超时（超过 {QUERY_TIMEOUT} 秒）") from exc
        finally:
            executor.shutdown(wait=False, cancel_futures=True)
            conn.close()
    else:
        columns, rows, _ = database_service.execute(connection, sql, limit=MAX_RESULT_ROWS)

    return {
        "columns": columns,
        "rows": rows,
        "row_count": len(rows),
        "execution_time": round(time.perf_counter() - started, 4),
    }


def _run_duckdb(conn, sql: str):
    cursor = conn.execute(sql)
    return _normalize_rows(cursor)
