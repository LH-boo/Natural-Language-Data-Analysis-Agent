from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func

from agent.graph import run_analysis
from api.serializers import loads
from models import (
    AnalysisReport,
    AnalysisTask,
    ChatMessage,
    Conversation,
    Dataset,
    DatabaseConnection,
    SqlExecutionLog,
)
from models.base import session_scope
from models.conversation import new_id
from utils.logger import get_logger

router = APIRouter(prefix="/api/analysis", tags=["智能分析"])
logger = get_logger("chat")


class ChatRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=2000)
    dataset_id: int | None = None
    connection_id: int | None = None
    conversation_id: str | None = None


def _build_payload(
    state: dict[str, Any], task: AnalysisTask, conversation_id: str, rows: list[dict]
) -> dict[str, Any]:
    return {
        "success": bool(state.get("success")),
        "conversation_id": conversation_id,
        "task_id": task.id,
        "question": task.question,
        "resolved_question": state.get("resolved_question", task.question),
        "sql": task.generated_sql,
        "sql_explanation": task.sql_explanation,
        "analysis": task.analysis_result,
        "chart": loads(task.chart_config, None),
        "chart_type": task.chart_type,
        "columns": loads(task.columns_json, []),
        "rows": rows,
        "row_count": task.row_count,
        "execution_time": task.execution_time,
        "steps": state.get("steps", []),
        "warnings": state.get("issues", []),
        "llm_used": task.llm_used,
        "dataset_id": task.dataset_id,
        "connection_id": task.connection_id,
        "created_at": task.created_at.isoformat(sep=" ") if task.created_at else None,
    }


@router.post("/chat")
def analysis_chat(request: ChatRequest):
    question = request.question.strip()
    if not question:
        raise HTTPException(status_code=400, detail="问题不能为空")
    if not request.dataset_id and not request.connection_id:
        raise HTTPException(status_code=400, detail="请先选择数据集或数据库连接")

    with session_scope() as session:
        dataset = session.get(Dataset, request.dataset_id) if request.dataset_id else None
        connection = (
            session.get(DatabaseConnection, request.connection_id) if request.connection_id else None
        )
        if request.dataset_id and not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")
        if request.connection_id and not connection:
            raise HTTPException(status_code=404, detail="数据库连接不存在")

        conversation = (
            session.get(Conversation, request.conversation_id) if request.conversation_id else None
        )
        if conversation is None:
            conversation = Conversation(
                id=request.conversation_id or new_id(),
                title=question[:30],
                dataset_id=request.dataset_id,
                connection_id=request.connection_id,
            )
            session.add(conversation)
            session.flush()
        else:
            conversation.dataset_id = request.dataset_id
            conversation.connection_id = request.connection_id
            if conversation.title in ("新的分析会话", ""):
                conversation.title = question[:30]

        previous = (
            session.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation.id)
            .order_by(ChatMessage.id.desc())
            .limit(10)
            .all()
        )
        history = [{"role": message.role, "content": message.content} for message in reversed(previous)]

        session.add(ChatMessage(conversation_id=conversation.id, role="user", content=question))
        conversation_id = conversation.id

    try:
        state = run_analysis(
            question=question,
            dataset_id=request.dataset_id,
            connection_id=request.connection_id,
            conversation_id=conversation_id,
            history=history,
        )
    except Exception as exc:
        logger.exception("Agent 执行异常")
        state = {
            "success": False,
            "analysis": f"分析流程执行失败：{exc}",
            "steps": [
                {
                    "key": "error",
                    "title": "Agent 执行异常",
                    "status": "error",
                    "detail": str(exc),
                }
            ],
            "issues": [str(exc)],
            "query_result": {},
        }

    query_result = state.get("query_result") or {}
    columns = query_result.get("columns", [])
    rows = query_result.get("rows", [])
    sql = state.get("safe_sql") or state.get("sql") or ""
    success = bool(state.get("success"))

    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if conversation is None:
            raise HTTPException(status_code=404, detail="会话不存在")

        task = AnalysisTask(
            conversation_id=conversation_id,
            dataset_id=request.dataset_id,
            connection_id=request.connection_id,
            question=question,
            generated_sql=sql,
            sql_explanation=state.get("sql_explanation", ""),
            execution_status="success" if success else "failed",
            analysis_result=state.get("analysis", ""),
            chart_type=state.get("chart_type", "table"),
            chart_config=json.dumps(state.get("chart_config"), ensure_ascii=False, default=str),
            columns_json=json.dumps(columns, ensure_ascii=False),
            rows_json=json.dumps(rows, ensure_ascii=False, default=str),
            row_count=len(rows),
            execution_time=float(query_result.get("execution_time", 0) or 0),
            llm_used=bool(state.get("llm_used")),
        )
        session.add(task)
        session.flush()

        session.add(
            SqlExecutionLog(
                task_id=task.id,
                dataset_id=request.dataset_id,
                sql_content=sql,
                execution_time=task.execution_time,
                result_count=len(rows),
                is_safe=bool(state.get("sql_valid")),
                error_message=state.get("error", ""),
            )
        )

        if success:
            session.add(
                AnalysisReport(
                    task_id=task.id,
                    title=question[:120],
                    summary=state.get("analysis", ""),
                    content=json.dumps(
                        {
                            "question": question,
                            "sql": sql,
                            "analysis": state.get("analysis", ""),
                            "columns": columns,
                            "rows": rows,
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                )
            )

        payload = _build_payload(state, task, conversation_id, rows)
        session.add(
            ChatMessage(
                conversation_id=conversation_id,
                role="assistant",
                content=state.get("analysis", ""),
                payload_json=json.dumps(payload, ensure_ascii=False, default=str),
            )
        )
        conversation.dataset_id = request.dataset_id
        conversation.connection_id = request.connection_id
        conversation.updated_at = datetime.now()
        return payload


@router.get("/conversations")
def list_conversations(limit: int = 50):
    with session_scope() as session:
        rows = (
            session.query(Conversation, func.count(ChatMessage.id))
            .outerjoin(ChatMessage, ChatMessage.conversation_id == Conversation.id)
            .group_by(Conversation.id)
            .order_by(Conversation.updated_at.desc())
            .limit(limit)
            .all()
        )
        return {
            "items": [
                {
                    "id": conversation.id,
                    "title": conversation.title,
                    "dataset_id": conversation.dataset_id,
                    "connection_id": conversation.connection_id,
                    "message_count": count,
                    "created_at": conversation.created_at.isoformat(sep=" ") if conversation.created_at else None,
                    "updated_at": conversation.updated_at.isoformat(sep=" ") if conversation.updated_at else None,
                }
                for conversation, count in rows
            ]
        }


@router.get("/conversations/{conversation_id}")
def get_conversation(conversation_id: str):
    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        messages = (
            session.query(ChatMessage)
            .filter(ChatMessage.conversation_id == conversation_id)
            .order_by(ChatMessage.id.asc())
            .all()
        )
        return {
            "conversation": {
                "id": conversation.id,
                "title": conversation.title,
                "dataset_id": conversation.dataset_id,
                "connection_id": conversation.connection_id,
                "created_at": conversation.created_at.isoformat(sep=" ") if conversation.created_at else None,
            },
            "messages": [
                {
                    "id": message.id,
                    "role": message.role,
                    "content": message.content,
                    "payload": loads(message.payload_json, None),
                    "created_at": message.created_at.isoformat(sep=" ") if message.created_at else None,
                }
                for message in messages
            ],
        }


@router.delete("/conversations/{conversation_id}")
def delete_conversation(conversation_id: str):
    with session_scope() as session:
        conversation = session.get(Conversation, conversation_id)
        if not conversation:
            raise HTTPException(status_code=404, detail="会话不存在")
        session.query(ChatMessage).filter(ChatMessage.conversation_id == conversation_id).delete()
        session.delete(conversation)
    return {"success": True, "message": "会话已删除"}
