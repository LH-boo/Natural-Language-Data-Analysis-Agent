from __future__ import annotations

import json
from typing import Any

from models import AnalysisReport, AnalysisTask, Conversation, Dataset


def loads(value: str | None, default: Any):
    if not value:
        return default
    try:
        return json.loads(value)
    except Exception:
        return default


def dataset_dict(dataset: Dataset, include_columns: bool = False) -> dict[str, Any]:
    payload = {
        "id": dataset.id,
        "name": dataset.name,
        "source_type": dataset.source_type,
        "table_name": dataset.table_name,
        "row_count": dataset.row_count,
        "column_count": dataset.column_count,
        "file_path": dataset.file_path,
        "created_at": dataset.created_at.isoformat(sep=" ") if dataset.created_at else None,
    }
    if include_columns:
        payload["columns"] = [
            {
                "name": column.name,
                "dtype": column.dtype,
                "description": column.description,
                "missing_count": column.missing_count,
                "unique_count": column.unique_count,
            }
            for column in dataset.columns
        ]
    return payload


def task_dict(task: AnalysisTask, include_rows: bool = False) -> dict[str, Any]:
    payload = {
        "id": task.id,
        "conversation_id": task.conversation_id,
        "dataset_id": task.dataset_id,
        "connection_id": task.connection_id,
        "question": task.question,
        "sql": task.generated_sql,
        "sql_explanation": task.sql_explanation,
        "status": task.execution_status,
        "analysis": task.analysis_result,
        "chart_type": task.chart_type,
        "chart": loads(task.chart_config, None),
        "columns": loads(task.columns_json, []),
        "row_count": task.row_count,
        "execution_time": task.execution_time,
        "llm_used": task.llm_used,
        "created_at": task.created_at.isoformat(sep=" ") if task.created_at else None,
    }
    if include_rows:
        payload["rows"] = loads(task.rows_json, [])
    return payload


def conversation_dict(conversation: Conversation, message_count: int = 0) -> dict[str, Any]:
    return {
        "id": conversation.id,
        "title": conversation.title,
        "dataset_id": conversation.dataset_id,
        "connection_id": conversation.connection_id,
        "message_count": message_count,
        "created_at": conversation.created_at.isoformat(sep=" ") if conversation.created_at else None,
        "updated_at": conversation.updated_at.isoformat(sep=" ") if conversation.updated_at else None,
    }


def report_dict(task: AnalysisTask, report: AnalysisReport | None = None) -> dict[str, Any]:
    payload = task_dict(task, include_rows=True)
    if report:
        payload["report_id"] = report.id
        payload["report_title"] = report.title
    return payload
