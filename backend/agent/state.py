from __future__ import annotations

from typing import Any, TypedDict


class AnalysisState(TypedDict, total=False):
    question: str
    resolved_question: str
    dataset_id: int | None
    connection_id: int | None
    conversation_id: str
    history: list[dict[str, str]]
    dialect: str
    schema: dict[str, Any]
    sql: str
    safe_sql: str
    sql_valid: bool
    sql_explanation: str
    issues: list[str]
    error: str
    query_result: dict[str, Any]
    analysis: str
    chart_config: dict[str, Any] | None
    chart_type: str
    steps: list[dict[str, Any]]
    retry_count: int
    llm_used: bool
    success: bool


def append_step(
    state: AnalysisState,
    key: str,
    title: str,
    status: str = "success",
    detail: str = "",
) -> list[dict[str, Any]]:
    steps = list(state.get("steps") or [])
    steps.append({"key": key, "title": title, "status": status, "detail": detail})
    return steps
