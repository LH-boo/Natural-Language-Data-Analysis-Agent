from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, DateTime, Float, ForeignKey, Integer, String, Text

from models.base import Base


def now() -> datetime:
    return datetime.now()


class AnalysisTask(Base):
    __tablename__ = "analysis_tasks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), index=True, nullable=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
    question = Column(Text, default="")
    generated_sql = Column(Text, default="")
    sql_explanation = Column(Text, default="")
    execution_status = Column(String(30), default="pending")
    analysis_result = Column(Text, default="")
    chart_type = Column(String(30), default="table")
    chart_config = Column(Text, default="")
    columns_json = Column(Text, default="[]")
    rows_json = Column(Text, default="[]")
    row_count = Column(BigInteger, default=0)
    execution_time = Column(Float, default=0)
    llm_used = Column(Boolean, default=False)
    created_at = Column(DateTime, default=now)


class SqlExecutionLog(Base):
    __tablename__ = "sql_execution_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, nullable=True)
    dataset_id = Column(Integer, nullable=True)
    sql_content = Column(Text, default="")
    execution_time = Column(Float, default=0)
    result_count = Column(Integer, default=0)
    is_safe = Column(Boolean, default=True)
    error_message = Column(Text, default="")
    created_at = Column(DateTime, default=now)


class AnalysisReport(Base):
    __tablename__ = "analysis_reports"

    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("analysis_tasks.id"), nullable=False, index=True)
    title = Column(String(255), default="")
    summary = Column(Text, default="")
    content = Column(Text, default="")
    created_at = Column(DateTime, default=now)
