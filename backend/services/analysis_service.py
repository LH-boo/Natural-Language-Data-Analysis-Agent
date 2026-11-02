from __future__ import annotations

import json
import math
import statistics
from typing import Any

from agent.llm import llm_client
from agent.prompts import ANALYSIS_SYSTEM, ANALYSIS_USER


def _numeric_values(rows: list[dict], column: str) -> list[float]:
    values = []
    for row in rows:
        value = row.get(column)
        if isinstance(value, bool) or value is None:
            continue
        if isinstance(value, (int, float)) and math.isfinite(float(value)):
            values.append(float(value))
    return values


def build_stats(columns: list[str], rows: list[dict]) -> tuple[dict[str, Any], str]:
    stats: dict[str, Any] = {"row_count": len(rows), "columns": {}}
    lines = [f"结果行数：{len(rows)}"]

    for column in columns:
        values = _numeric_values(rows, column)
        if not values:
            continue
        item = {
            "count": len(values),
            "sum": round(sum(values), 4),
            "avg": round(statistics.fmean(values), 4),
            "min": round(min(values), 4),
            "max": round(max(values), 4),
        }
        if len(values) > 1:
            item["std"] = round(statistics.pstdev(values), 4)
        stats["columns"][column] = item
        lines.append(
            f"{column}：合计 {item['sum']}，平均 {item['avg']}，最小 {item['min']}，最大 {item['max']}"
        )

    return stats, "\n".join(lines)


def _fallback_analysis(question: str, columns: list[str], rows: list[dict], stats: dict[str, Any]) -> str:
    if not rows:
        return "查询结果为空。建议检查筛选条件、时间范围，或确认数据集中是否存在对应数据。"

    parts = [f"本次查询共返回 {len(rows)} 行数据。"]
    numeric_items = list(stats.get("columns", {}).items())
    if numeric_items:
        column, item = numeric_items[0]
        parts.append(
            f"「{column}」合计为 {item['sum']}，平均为 {item['avg']}，最高为 {item['max']}，最低为 {item['min']}。"
        )

        dimension = next((column for column in columns if column not in stats.get("columns", {})), None)
        if dimension and len(rows) > 1:
            target = numeric_items[0][0]
            ranked = sorted(
                [row for row in rows if isinstance(row.get(target), (int, float))],
                key=lambda row: row.get(target, 0),
                reverse=True,
            )
            if len(ranked) >= 2:
                top, bottom = ranked[0], ranked[-1]
                parts.append(
                    f"排名首位的「{top.get(dimension)}」为 {top.get(target)}；"
                    f"排名末位的「{bottom.get(dimension)}」为 {bottom.get(target)}。"
                )

        std = item.get("std")
        if std and std > 0:
            mean = item["avg"]
            anomalies = [
                row
                for row in rows
                if isinstance(row.get(column), (int, float))
                and abs(row[column] - mean) > 2 * std
            ]
            if anomalies:
                parts.append(
                    f"检测到 {len(anomalies)} 个偏离均值超过两倍标准差的异常值，建议进一步核查对应记录。"
                )
    else:
        first = rows[0]
        parts.append(f"首条记录的关键字段为：{', '.join(f'{k}={v}' for k, v in list(first.items())[:4])}。")

    parts.append("以上结论基于数据库真实查询结果，未使用模型推测数据。")
    return "".join(parts)


def analyze_result(
    question: str,
    sql: str,
    columns: list[str],
    rows: list[dict],
    chart_type: str = "",
) -> dict[str, Any]:
    stats, stats_text = build_stats(columns, rows)
    if not rows:
        return {
            "analysis": _fallback_analysis(question, columns, rows, stats),
            "stats": stats,
            "llm_used": False,
        }

    sample_rows = rows[:50]
    content = llm_client.chat_text(
        ANALYSIS_SYSTEM,
        ANALYSIS_USER.format(
            question=question,
            sql=sql,
            rows=json.dumps(sample_rows, ensure_ascii=False, default=str),
            stats=stats_text,
        ),
    )
    if content:
        return {"analysis": content.strip(), "stats": stats, "llm_used": True}
    return {
        "analysis": _fallback_analysis(question, columns, rows, stats),
        "stats": stats,
        "llm_used": False,
    }
