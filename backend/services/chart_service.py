from __future__ import annotations

from typing import Any

PALETTE = ["#4f7cff", "#22c3a6", "#f6a93b", "#ef5b7b", "#8b5cf6", "#38bdf8", "#f97316", "#14b8a6"]


def _numeric_columns(columns: list[str], rows: list[dict]) -> list[str]:
    result = []
    for column in columns:
        values = [row.get(column) for row in rows if row.get(column) is not None][:20]
        if values and all(isinstance(value, (int, float)) and not isinstance(value, bool) for value in values):
            result.append(column)
    return result


def _time_like(column: str) -> bool:
    lowered = str(column).lower()
    return any(token in lowered for token in ("日期", "时间", "月份", "年份", "date", "time", "month", "year"))


def build_chart(
    question: str,
    columns: list[str],
    rows: list[dict],
    chart_type: str = "bar",
) -> dict[str, Any]:
    if not rows or not columns:
        return {"type": "table", "option": None}

    numeric = _numeric_columns(columns, rows)
    if not numeric:
        return {"type": "table", "option": None}

    dimensions = [column for column in columns if column not in numeric]
    dimension = dimensions[0] if dimensions else columns[0]
    lowered = question.lower()

    if any(token in question for token in ("占比", "比例", "构成", "分布")) and chart_type not in ("table",):
        chart_type = "pie"
    if dimension and _time_like(dimension):
        chart_type = "line"
    if chart_type in ("", "table") and len(rows) > 1:
        chart_type = "bar"

    title = question.strip()[:28] or "分析结果"
    categories = [str(row.get(dimension, "")) for row in rows]

    if chart_type == "pie":
        value_column = numeric[0]
        data = [
            {"name": str(row.get(dimension, f"记录{i + 1}")), "value": row.get(value_column, 0)}
            for i, row in enumerate(rows[:12])
        ]
        option = {
            "color": PALETTE,
            "title": {"text": title, "left": "center", "textStyle": {"fontSize": 15, "fontWeight": 600}},
            "tooltip": {"trigger": "item"},
            "legend": {"bottom": 0, "type": "scroll"},
            "series": [
                {
                    "name": value_column,
                    "type": "pie",
                    "radius": ["42%", "68%"],
                    "center": ["50%", "48%"],
                    "itemStyle": {"borderRadius": 6, "borderColor": "#fff", "borderWidth": 2},
                    "label": {"formatter": "{b}\n{d}%"},
                    "data": data,
                }
            ],
        }
        return {"type": "pie", "option": option}

    if chart_type == "scatter" and len(numeric) >= 2:
        x_column, y_column = numeric[0], numeric[1]
        option = {
            "color": PALETTE,
            "title": {"text": title, "left": "center", "textStyle": {"fontSize": 15, "fontWeight": 600}},
            "tooltip": {"trigger": "item"},
            "xAxis": {"type": "value", "name": x_column, "splitLine": {"lineStyle": {"type": "dashed"}}},
            "yAxis": {"type": "value", "name": y_column, "splitLine": {"lineStyle": {"type": "dashed"}}},
            "grid": {"left": 56, "right": 28, "top": 56, "bottom": 48},
            "series": [
                {
                    "type": "scatter",
                    "symbolSize": 11,
                    "data": [[row.get(x_column), row.get(y_column)] for row in rows],
                }
            ],
        }
        return {"type": "scatter", "option": option}

    if chart_type not in ("bar", "line"):
        chart_type = "bar"

    series = []
    for index, column in enumerate(numeric[:4]):
        item = {
            "name": column,
            "type": chart_type,
            "smooth": chart_type == "line",
            "barMaxWidth": 36,
            "symbolSize": 6,
            "data": [row.get(column) for row in rows],
        }
        if chart_type == "line":
            item["areaStyle"] = {"opacity": 0.12}
        else:
            item["itemStyle"] = {"borderRadius": [5, 5, 0, 0]}
        series.append(item)

    option = {
        "color": PALETTE,
        "title": {"text": title, "left": "center", "textStyle": {"fontSize": 15, "fontWeight": 600}},
        "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
        "legend": {"top": 26, "type": "scroll"},
        "grid": {"left": 56, "right": 28, "top": 68, "bottom": 56, "containLabel": True},
        "xAxis": {
            "type": "category",
            "data": categories,
            "axisLabel": {"rotate": 28 if len(categories) > 7 else 0, "color": "#64748b"},
            "axisLine": {"lineStyle": {"color": "#cbd5e1"}},
        },
        "yAxis": {
            "type": "value",
            "splitLine": {"lineStyle": {"type": "dashed", "color": "#e2e8f0"}},
            "axisLabel": {"color": "#64748b"},
        },
        "series": series,
    }
    if len(categories) > 16:
        option["dataZoom"] = [
            {"type": "inside", "start": 0, "end": 60},
            {"type": "slider", "height": 16, "bottom": 8, "start": 0, "end": 60},
        ]
    return {"type": chart_type, "option": option}


def empty_chart() -> dict[str, Any]:
    return {"type": "table", "option": None}
