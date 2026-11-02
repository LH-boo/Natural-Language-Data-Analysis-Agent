from __future__ import annotations

from typing import Any

from agent.llm import llm_client
from agent.prompts import REWRITE_SYSTEM, REWRITE_USER
from agent.state import AnalysisState, append_step
from models import DatabaseConnection, Dataset
from models.base import session_scope
from services.analysis_service import analyze_result
from services.chart_service import build_chart
from services.schema_service import get_connection_schema, get_dataset_schema
from services.sql_service import execute_sql, generate_sql, repair_sql
from security.sql_validator import validate_sql


def _history_text(history: list[dict[str, str]]) -> str:
    return "\n".join(f"{item['role']}：{item['content'][:200]}" for item in history[-6:])


def question_node(state: AnalysisState) -> dict[str, Any]:
    question = (state.get("question") or "").strip()
    history = state.get("history") or []
    resolved = question

    follow_up = any(
        question.startswith(prefix) for prefix in ("再", "那", "只看", "改成", "换成", "按", "继续", "它")
    ) or len(question) <= 8
    if follow_up and history:
        rewritten = llm_client.chat_text(
            REWRITE_SYSTEM, REWRITE_USER.format(history=_history_text(history), question=question)
        )
        if rewritten:
            resolved = rewritten.strip().splitlines()[0][:300]
        else:
            last_question = next(
                (item["content"] for item in reversed(history) if item["role"] == "user"), ""
            )
            if last_question:
                resolved = f"{question}；在上一轮问题基础上：{last_question}"[:300]

    return {
        "resolved_question": resolved,
        "sql": "",
        "safe_sql": "",
        "sql_valid": False,
        "issues": [],
        "error": "",
        "query_result": {},
        "analysis": "",
        "chart_config": None,
        "chart_type": "",
        "retry_count": 0,
        "llm_used": llm_client.configured,
        "success": False,
        "steps": [
            {
                "key": "question",
                "title": "理解用户问题",
                "status": "success",
                "detail": f"已识别问题：{resolved[:80]}",
            }
        ],
    }


def schema_node(state: AnalysisState) -> dict[str, Any]:
    try:
        with session_scope() as session:
            if state.get("dataset_id"):
                schema = get_dataset_schema(session, int(state["dataset_id"]))
                dialect = "duckdb"
            elif state.get("connection_id"):
                schema = get_connection_schema(session, int(state["connection_id"]))
                connection = session.get(DatabaseConnection, int(state["connection_id"]))
                dialect = "mysql" if connection and connection.db_type == "mysql" else "postgres"
            else:
                raise ValueError("请先选择数据集或数据库连接")
    except Exception as exc:
        return {
            "schema": {},
            "error": str(exc),
            "steps": append_step(state, "schema", "获取数据结构", "error", str(exc)),
        }

    count = len(schema.get("tables", [])) if "tables" in schema else len(schema.get("columns", []))
    detail = f"已加载 {count} 个字段" if "columns" in schema else f"已加载 {count} 张表"
    return {
        "schema": schema,
        "dialect": dialect,
        "steps": append_step(state, "schema", "获取数据结构", "success", detail),
    }


def sql_generate_node(state: AnalysisState) -> dict[str, Any]:
    try:
        result = generate_sql(
            state.get("resolved_question") or state.get("question", ""),
            state.get("schema") or {},
            state.get("history") or [],
        )
    except Exception as exc:
        return {
            "error": str(exc),
            "steps": append_step(state, "generate", "生成 SQL", "error", str(exc)),
        }

    source = "大模型" if result.get("llm_used") else "规则引擎"
    return {
        "sql": result["sql"],
        "sql_explanation": result.get("explanation", ""),
        "chart_type": result.get("chart_type", "bar"),
        "llm_used": bool(result.get("llm_used")),
        "steps": append_step(
            state, "generate", "生成 SQL", "success", f"{source}已生成查询语句"
        ),
    }


def sql_validate_node(state: AnalysisState) -> dict[str, Any]:
    schema = state.get("schema") or {}
    if "tables" in schema:
        allowed = schema.get("allowed_tables") or [table["name"] for table in schema["tables"]]
    else:
        allowed = [schema.get("table_name")] if schema.get("table_name") else []

    result = validate_sql(
        state.get("sql", ""),
        allowed_tables=[table for table in allowed if table],
        dialect=state.get("dialect", "duckdb"),
    )
    detail = "SQL 通过只读与表白名单校验" if result["valid"] else "；".join(result["issues"])
    return {
        "safe_sql": result["safe_sql"],
        "sql_valid": result["valid"],
        "issues": result["issues"],
        "error": "" if result["valid"] else detail,
        "steps": append_step(
            state,
            "validate",
            "SQL 安全校验",
            "success" if result["valid"] else "warning",
            detail,
        ),
    }


def sql_execute_node(state: AnalysisState) -> dict[str, Any]:
    try:
        with session_scope() as session:
            dataset = session.get(Dataset, int(state["dataset_id"])) if state.get("dataset_id") else None
            connection = (
                session.get(DatabaseConnection, int(state["connection_id"]))
                if state.get("connection_id")
                else None
            )
            if dataset is None and connection is None:
                raise ValueError("数据集或数据库连接不存在")
            result = execute_sql(state.get("safe_sql") or state.get("sql", ""), dataset, connection)
    except Exception as exc:
        return {
            "error": str(exc),
            "steps": append_step(state, "execute", "执行查询", "error", str(exc)),
        }

    return {
        "query_result": result,
        "error": "",
        "steps": append_step(
            state,
            "execute",
            "执行查询",
            "success",
            f"返回 {result['row_count']} 行，耗时 {result['execution_time']} 秒",
        ),
    }


def sql_repair_node(state: AnalysisState) -> dict[str, Any]:
    retry = int(state.get("retry_count") or 0) + 1
    error = state.get("error") or "；".join(state.get("issues") or []) or "SQL 执行失败"
    result = repair_sql(
        state.get("resolved_question") or state.get("question", ""),
        state.get("schema") or {},
        state.get("sql", ""),
        error,
    )
    return {
        "sql": result["sql"],
        "sql_explanation": result.get("explanation", ""),
        "chart_type": result.get("chart_type", "bar"),
        "retry_count": retry,
        "sql_valid": False,
        "error": "",
        "issues": [],
        "llm_used": bool(result.get("llm_used")),
        "steps": append_step(
            state,
            "repair",
            "修复 SQL",
            "warning",
            f"第 {retry} 次修复：{result.get('explanation', '重新生成查询')}",
        ),
    }


def analysis_node(state: AnalysisState) -> dict[str, Any]:
    query_result = state.get("query_result") or {}
    result = analyze_result(
        state.get("resolved_question") or state.get("question", ""),
        state.get("safe_sql") or state.get("sql", ""),
        query_result.get("columns", []),
        query_result.get("rows", []),
        state.get("chart_type", ""),
    )
    return {
        "analysis": result["analysis"],
        "llm_used": bool(result.get("llm_used")),
        "steps": append_step(
            state,
            "analysis",
            "分析查询结果",
            "success",
            "已生成基于真实数据的分析结论",
        ),
    }


def chart_node(state: AnalysisState) -> dict[str, Any]:
    query_result = state.get("query_result") or {}
    chart = build_chart(
        state.get("resolved_question") or state.get("question", ""),
        query_result.get("columns", []),
        query_result.get("rows", []),
        state.get("chart_type", "bar"),
    )
    detail = "已生成可视化图表" if chart.get("option") else "当前结果以表格展示"
    return {
        "chart_config": chart.get("option"),
        "chart_type": chart.get("type", "table"),
        "steps": append_step(state, "chart", "生成图表配置", "success", detail),
    }


def response_node(state: AnalysisState) -> dict[str, Any]:
    if state.get("error"):
        message = f"分析未能完成：{state['error']}。请调整问题、检查数据字段或稍后重试。"
        return {
            "analysis": message,
            "success": False,
            "chart_type": "table",
            "chart_config": None,
            "steps": append_step(state, "response", "汇总回答", "error", "已返回错误说明"),
        }
    return {
        "success": True,
        "steps": append_step(state, "response", "汇总回答", "success", "分析流程已完成"),
    }
