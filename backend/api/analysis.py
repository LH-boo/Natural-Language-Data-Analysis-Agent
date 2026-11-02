from __future__ import annotations

import csv
import html
import io
import json
import time
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import func

from agent.llm import llm_client
from api.serializers import loads, task_dict
from config import APP_START_TIME, APP_VERSION, DUCKDB_PATH, LLM_MODEL, METADATA_DATABASE_URL
from models import (
    AnalysisReport,
    AnalysisTask,
    Conversation,
    Dataset,
    DatabaseConnection,
    SqlExecutionLog,
)
from models.base import session_scope
from services import sql_service
from services.chart_service import build_chart
from services.database_service import database_service
from services.schema_service import get_connection_schema, get_dataset_schema
from utils.data import quote_ident
from utils.logger import get_logger
from security.sql_validator import validate_sql

router = APIRouter(prefix="/api/analysis", tags=["分析结果"])
logger = get_logger("analysis")


class SqlRequest(BaseModel):
    sql: str = Field(..., min_length=1)
    dataset_id: int | None = None
    connection_id: int | None = None


class ChartRequest(BaseModel):
    dataset_id: int
    dimension: str
    metric: str = ""
    agg: str = "sum"
    chart_type: str = "bar"


def _log_dict(log: SqlExecutionLog) -> dict[str, Any]:
    return {
        "id": log.id,
        "task_id": log.task_id,
        "dataset_id": log.dataset_id,
        "sql": log.sql_content,
        "execution_time": log.execution_time,
        "result_count": log.result_count,
        "is_safe": log.is_safe,
        "error_message": log.error_message,
        "created_at": log.created_at.isoformat(sep=" ") if log.created_at else None,
    }


def _dataset_names(session, dataset_ids: set[int]) -> dict[int, str]:
    if not dataset_ids:
        return {}
    rows = session.query(Dataset.id, Dataset.name).filter(Dataset.id.in_(dataset_ids)).all()
    return {row[0]: row[1] for row in rows}


@router.post("/sql")
def execute_sql_endpoint(request: SqlRequest):
    if not request.dataset_id and not request.connection_id:
        raise HTTPException(status_code=400, detail="请选择数据集或数据库连接")

    with session_scope() as session:
        dataset = session.get(Dataset, request.dataset_id) if request.dataset_id else None
        connection = (
            session.get(DatabaseConnection, request.connection_id) if request.connection_id else None
        )
        if dataset is None and connection is None:
            raise HTTPException(status_code=404, detail="数据集或数据库连接不存在")
        try:
            if dataset:
                schema = get_dataset_schema(session, dataset.id)
                allowed = [schema["table_name"]]
                dialect = "duckdb"
            else:
                schema = get_connection_schema(session, connection.id)
                allowed = schema.get("allowed_tables", [])
                dialect = "mysql" if connection.db_type == "mysql" else "postgres"
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        validation = validate_sql(request.sql, allowed_tables=allowed, dialect=dialect)
        if not validation["valid"]:
            session.add(
                SqlExecutionLog(
                    dataset_id=request.dataset_id,
                    sql_content=request.sql,
                    is_safe=False,
                    error_message="；".join(validation["issues"]),
                )
            )
            return {
                "success": False,
                "sql": request.sql,
                "issues": validation["issues"],
                "message": "SQL 未通过安全校验",
            }

        try:
            result = sql_service.execute_sql(validation["safe_sql"], dataset, connection)
        except Exception as exc:
            session.add(
                SqlExecutionLog(
                    dataset_id=request.dataset_id,
                    sql_content=validation["safe_sql"],
                    is_safe=True,
                    error_message=str(exc),
                )
            )
            return {"success": False, "sql": validation["safe_sql"], "issues": [str(exc)]}

        session.add(
            SqlExecutionLog(
                dataset_id=request.dataset_id,
                sql_content=validation["safe_sql"],
                execution_time=result["execution_time"],
                result_count=result["row_count"],
                is_safe=True,
            )
        )
        return {
            "success": True,
            "sql": validation["safe_sql"],
            "sql_explanation": "手工 SQL 查询",
            **result,
        }


@router.post("/chart")
def build_dataset_chart(request: ChartRequest):
    with session_scope() as session:
        dataset = session.get(Dataset, request.dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")
        schema = get_dataset_schema(session, dataset.id)
        column_names = {column["name"] for column in schema["columns"]}
        if request.dimension not in column_names:
            raise HTTPException(status_code=400, detail="维度字段不存在")
        agg = request.agg.lower()
        if agg not in ("sum", "avg", "count", "max", "min"):
            raise HTTPException(status_code=400, detail="不支持的聚合方式")

        if agg == "count":
            metric_sql = "COUNT(*)"
            metric_alias = "记录数"
        else:
            if request.metric not in column_names:
                raise HTTPException(status_code=400, detail="指标字段不存在")
            metric_sql = f"{agg.upper()}({quote_ident(request.metric)})"
            metric_alias = request.metric

        sql = (
            f'SELECT {quote_ident(request.dimension)} AS "维度", {metric_sql} AS "{metric_alias}" '
            f'FROM {quote_ident(dataset.table_name)} GROUP BY 1 ORDER BY 2 DESC LIMIT 50'
        )
        validation = validate_sql(sql, allowed_tables=[dataset.table_name], dialect="duckdb")
        if not validation["valid"]:
            raise HTTPException(status_code=400, detail="；".join(validation["issues"]))
        try:
            result = sql_service.execute_sql(validation["safe_sql"], dataset=dataset)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"图表数据查询失败：{exc}") from exc

    chart = build_chart(
        f"{request.dimension}与{metric_alias}对比", result["columns"], result["rows"], request.chart_type
    )
    return {
        "success": True,
        "sql": validation["safe_sql"],
        "chart": chart.get("option"),
        "chart_type": chart.get("type"),
        **result,
    }


@router.get("/history")
def analysis_history(limit: int = Query(50, ge=1, le=200)):
    with session_scope() as session:
        tasks = session.query(AnalysisTask).order_by(AnalysisTask.id.desc()).limit(limit).all()
        names = _dataset_names(session, {task.dataset_id for task in tasks if task.dataset_id})
        items = []
        for task in tasks:
            item = task_dict(task)
            item["dataset_name"] = names.get(task.dataset_id, "外部数据库" if task.connection_id else "-")
            items.append(item)
        return {"items": items}


@router.get("/reports")
def list_reports(limit: int = Query(50, ge=1, le=200)):
    with session_scope() as session:
        tasks = (
            session.query(AnalysisTask)
            .filter(AnalysisTask.execution_status == "success")
            .order_by(AnalysisTask.id.desc())
            .limit(limit)
            .all()
        )
        names = _dataset_names(session, {task.dataset_id for task in tasks if task.dataset_id})
        reports = {
            report.task_id: report
            for report in session.query(AnalysisReport)
            .filter(AnalysisReport.task_id.in_([task.id for task in tasks] or [0]))
            .all()
        }
        items = []
        for task in tasks:
            item = task_dict(task)
            item["dataset_name"] = names.get(task.dataset_id, "-")
            item["report_id"] = reports.get(task.id).id if reports.get(task.id) else None
            items.append(item)
        return {"items": items}


@router.get("/reports/{task_id}")
def report_detail(task_id: int):
    with session_scope() as session:
        task = session.get(AnalysisTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="分析记录不存在")
        dataset = session.get(Dataset, task.dataset_id) if task.dataset_id else None
        report = session.query(AnalysisReport).filter(AnalysisReport.task_id == task_id).first()
        payload = task_dict(task, include_rows=True)
        payload["dataset_name"] = dataset.name if dataset else ("外部数据库" if task.connection_id else "-")
        payload["report"] = {
            "id": report.id,
            "title": report.title,
            "summary": report.summary,
            "created_at": report.created_at.isoformat(sep=" ") if report and report.created_at else None,
        } if report else None
        return payload


@router.get("/export/{task_id}")
def export_report(task_id: int, format: str = Query("csv", pattern="^(csv|json|html)$")):
    with session_scope() as session:
        task = session.get(AnalysisTask, task_id)
        if not task:
            raise HTTPException(status_code=404, detail="分析记录不存在")
        dataset = session.get(Dataset, task.dataset_id) if task.dataset_id else None
        rows = loads(task.rows_json, [])
        columns = loads(task.columns_json, [])
        title = task.question
        analysis = task.analysis_result
        sql = task.generated_sql

    if format == "json":
        content = json.dumps(
            {
                "question": title,
                "sql": sql,
                "analysis": analysis,
                "columns": columns,
                "rows": rows,
            },
            ensure_ascii=False,
            indent=2,
        )
        media_type = "application/json"
        extension = "json"
    elif format == "csv":
        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columns or ["结果"])
        writer.writeheader()
        for row in rows:
            writer.writerow({column: row.get(column, "") for column in (columns or ["结果"])})
        content = "\ufeff" + buffer.getvalue()
        media_type = "text/csv; charset=utf-8"
        extension = "csv"
    else:
        header = "".join(f"<th>{html.escape(str(column))}</th>" for column in columns)
        body_rows = "".join(
            "<tr>" + "".join(f"<td>{html.escape(str(row.get(column, '')))}</td>" for column in columns) + "</tr>"
            for row in rows
        )
        content = f"""<!DOCTYPE html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>{html.escape(title)}</title>
<style>
body{{font-family:-apple-system,"Microsoft YaHei",sans-serif;background:#f5f7fb;color:#0f172a;padding:40px;line-height:1.7}}
.card{{max-width:960px;margin:0 auto;background:#fff;border-radius:16px;padding:32px;box-shadow:0 10px 30px rgba(15,23,42,.08)}}
h1{{font-size:22px}} .meta{{color:#64748b;font-size:13px}} pre{{background:#0f172a;color:#dbeafe;padding:16px;border-radius:10px;overflow:auto;font-size:12px}}
table{{border-collapse:collapse;width:100%;margin-top:16px;font-size:13px}} th,td{{border:1px solid #e2e8f0;padding:8px 10px;text-align:left}}
th{{background:#f1f5f9}} .analysis{{background:#eef4ff;border-left:4px solid #4f7cff;padding:14px 18px;border-radius:8px}}
</style></head><body><div class="card">
<h1>{html.escape(title)}</h1>
<p class="meta">数据集：{html.escape(dataset.name if dataset else "外部数据库")} · 返回 {len(rows)} 行</p>
<div class="analysis">{html.escape(analysis)}</div>
<h3>查询语句</h3><pre>{html.escape(sql)}</pre>
<h3>数据明细</h3><table><thead><tr>{header}</tr></thead><tbody>{body_rows}</tbody></table>
</div></body></html>"""
        media_type = "text/html; charset=utf-8"
        extension = "html"

    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename=analysis_report_{task_id}.{extension}"},
    )


@router.get("/sql-logs")
def sql_logs(limit: int = Query(100, ge=1, le=500)):
    with session_scope() as session:
        logs = session.query(SqlExecutionLog).order_by(SqlExecutionLog.id.desc()).limit(limit).all()
        return {"items": [_log_dict(log) for log in logs]}


@router.get("/dashboard")
def dashboard():
    today = datetime.now().date()
    with session_scope() as session:
        dataset_count = session.query(func.count(Dataset.id)).scalar() or 0
        task_count = session.query(func.count(AnalysisTask.id)).scalar() or 0
        conversation_count = session.query(func.count(Conversation.id)).scalar() or 0
        report_count = session.query(func.count(AnalysisReport.id)).scalar() or 0
        avg_time = session.query(func.avg(AnalysisTask.execution_time)).scalar() or 0

        recent_tasks = session.query(AnalysisTask).order_by(AnalysisTask.id.desc()).limit(8).all()
        names = _dataset_names(session, {task.dataset_id for task in recent_tasks if task.dataset_id})

        chart_counts: dict[str, int] = {}
        for (chart_type,) in session.query(AnalysisTask.chart_type).all():
            key = chart_type or "table"
            chart_counts[key] = chart_counts.get(key, 0) + 1

        all_tasks = session.query(AnalysisTask.created_at).all()
        daily = []
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            count = sum(1 for (created_at,) in all_tasks if created_at and created_at.date() == day)
            daily.append({"date": day.strftime("%m-%d"), "count": count})

        recent = []
        for task in recent_tasks:
            item = task_dict(task)
            item["dataset_name"] = names.get(task.dataset_id, "外部数据库" if task.connection_id else "-")
            recent.append(item)

        return {
            "stats": {
                "dataset_count": dataset_count,
                "task_count": task_count,
                "conversation_count": conversation_count,
                "report_count": report_count,
                "avg_execution_time": round(float(avg_time), 4),
                "llm_configured": llm_client.configured,
            },
            "recent_tasks": recent,
            "chart_distribution": [
                {"name": name, "value": value} for name, value in sorted(chart_counts.items(), key=lambda item: -item[1])
            ],
            "daily_tasks": daily,
        }


@router.get("/monitoring")
def monitoring():
    with session_scope() as session:
        dataset_count = session.query(func.count(Dataset.id)).scalar() or 0
        task_count = session.query(func.count(AnalysisTask.id)).scalar() or 0
        log_count = session.query(func.count(SqlExecutionLog.id)).scalar() or 0
        error_count = (
            session.query(func.count(SqlExecutionLog.id))
            .filter(SqlExecutionLog.error_message != "")
            .scalar()
            or 0
        )
        blocked_count = (
            session.query(func.count(SqlExecutionLog.id))
            .filter(SqlExecutionLog.is_safe.is_(False))
            .scalar()
            or 0
        )
        avg_time = session.query(func.avg(SqlExecutionLog.execution_time)).scalar() or 0
        logs = session.query(SqlExecutionLog).order_by(SqlExecutionLog.id.desc()).limit(30).all()

        return {
            "status": "running",
            "version": APP_VERSION,
            "uptime_seconds": int(time.time() - APP_START_TIME),
            "llm": {
                "configured": llm_client.configured,
                "model": LLM_MODEL,
                "base_url": llm_client.base_url,
            },
            "storage": {
                "metadata": METADATA_DATABASE_URL.split("///")[-1],
                "duckdb": DUCKDB_PATH,
            },
            "counts": {
                "datasets": dataset_count,
                "tasks": task_count,
                "sql_logs": log_count,
                "errors": error_count,
                "blocked": blocked_count,
                "avg_execution_time": round(float(avg_time), 4),
            },
            "recent_logs": [_log_dict(log) for log in logs],
        }
