from __future__ import annotations

from typing import Any

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from agent.nodes import (
    analysis_node,
    chart_node,
    question_node,
    response_node,
    schema_node,
    sql_execute_node,
    sql_generate_node,
    sql_repair_node,
    sql_validate_node,
)
from agent.state import AnalysisState
from config import MAX_REPAIR


def _after_schema(state: AnalysisState) -> str:
    return "response" if state.get("error") else "generate"


def _after_generate(state: AnalysisState) -> str:
    return "response" if state.get("error") else "validate"


def _after_validate(state: AnalysisState) -> str:
    if state.get("sql_valid"):
        return "execute"
    if int(state.get("retry_count") or 0) < MAX_REPAIR:
        return "repair"
    return "response"


def _after_execute(state: AnalysisState) -> str:
    if not state.get("error"):
        return "analysis"
    if int(state.get("retry_count") or 0) < MAX_REPAIR:
        return "repair"
    return "response"


def build_graph():
    builder = StateGraph(AnalysisState)
    builder.add_node("question", question_node)
    builder.add_node("schema", schema_node)
    builder.add_node("generate", sql_generate_node)
    builder.add_node("validate", sql_validate_node)
    builder.add_node("execute", sql_execute_node)
    builder.add_node("repair", sql_repair_node)
    builder.add_node("analysis", analysis_node)
    builder.add_node("chart", chart_node)
    builder.add_node("response", response_node)

    builder.add_edge(START, "question")
    builder.add_edge("question", "schema")
    builder.add_conditional_edges(
        "schema", _after_schema, {"generate": "generate", "response": "response"}
    )
    builder.add_conditional_edges(
        "generate", _after_generate, {"validate": "validate", "response": "response"}
    )
    builder.add_conditional_edges(
        "validate",
        _after_validate,
        {"execute": "execute", "repair": "repair", "response": "response"},
    )
    builder.add_conditional_edges(
        "execute",
        _after_execute,
        {"analysis": "analysis", "repair": "repair", "response": "response"},
    )
    builder.add_edge("repair", "validate")
    builder.add_edge("analysis", "chart")
    builder.add_edge("chart", "response")
    builder.add_edge("response", END)
    return builder.compile(checkpointer=MemorySaver())


analysis_graph = build_graph()


def run_analysis(
    question: str,
    dataset_id: int | None = None,
    connection_id: int | None = None,
    conversation_id: str = "default",
    history: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    initial: AnalysisState = {
        "question": question,
        "resolved_question": question,
        "dataset_id": dataset_id,
        "connection_id": connection_id,
        "conversation_id": conversation_id,
        "history": history or [],
        "steps": [],
        "retry_count": 0,
        "success": False,
    }
    config = {
        "configurable": {"thread_id": conversation_id},
        "recursion_limit": 30,
    }
    return analysis_graph.invoke(initial, config=config)
