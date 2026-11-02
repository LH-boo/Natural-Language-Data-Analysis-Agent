from __future__ import annotations

import base64
from typing import Any
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect, text

from models import DatabaseConnection
from services.schema_service import describe_column
from utils.data import _convert


class DatabaseService:
    @staticmethod
    def encode_password(password: str) -> str:
        if not password:
            return ""
        return base64.b64encode(password.encode("utf-8")).decode("ascii")

    @staticmethod
    def decode_password(password: str) -> str:
        if not password:
            return ""
        try:
            return base64.b64decode(password.encode("ascii")).decode("utf-8")
        except Exception:
            return password

    def build_url(self, config: dict[str, Any]) -> str:
        db_type = (config.get("db_type") or "mysql").lower()
        if db_type == "sqlite":
            path = str(config.get("sqlite_path") or "").replace("\\", "/")
            if not path:
                raise ValueError("请填写 SQLite 数据库文件路径")
            return f"sqlite:///{path}"

        username = quote_plus(str(config.get("username") or ""))
        password = quote_plus(str(config.get("password") or ""))
        host = config.get("host") or "127.0.0.1"
        port = int(config.get("port") or (3306 if db_type == "mysql" else 5432))
        database = config.get("database_name") or ""
        if not database:
            raise ValueError("请填写数据库名称")

        if db_type == "mysql":
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}?charset=utf8mb4"
        if db_type in ("postgresql", "postgres"):
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        raise ValueError(f"暂不支持的数据库类型：{db_type}")

    def connection_config(self, connection: DatabaseConnection) -> dict[str, Any]:
        return {
            "db_type": connection.db_type,
            "host": connection.host,
            "port": connection.port,
            "username": connection.username,
            "password": self.decode_password(connection.password),
            "database_name": connection.database_name,
            "sqlite_path": connection.sqlite_path,
        }

    def test(self, config: dict[str, Any]) -> dict[str, Any]:
        url = self.build_url(config)
        engine = create_engine(url, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return {"success": True, "message": "连接成功"}
        finally:
            engine.dispose()

    def get_schema(self, connection: DatabaseConnection, max_tables: int = 30) -> dict[str, Any]:
        engine = create_engine(self.build_url(self.connection_config(connection)), pool_pre_ping=True)
        try:
            inspector = inspect(engine)
            tables = inspector.get_table_names()[:max_tables]
            result = []
            for table in tables:
                columns = []
                for column in inspector.get_columns(table):
                    dtype = str(column.get("type", ""))
                    columns.append(
                        {
                            "name": column["name"],
                            "dtype": dtype,
                            "description": describe_column(column["name"], dtype),
                            "nullable": bool(column.get("nullable", True)),
                        }
                    )
                result.append({"name": table, "columns": columns, "row_count": 0})
            return {
                "source_type": "database",
                "connection_id": connection.id,
                "connection_name": connection.name,
                "tables": result,
                "allowed_tables": [table["name"] for table in result],
            }
        finally:
            engine.dispose()

    def execute(
        self, connection: DatabaseConnection, sql: str, limit: int = 500
    ) -> tuple[list[str], list[dict], float]:
        import time

        engine = create_engine(self.build_url(self.connection_config(connection)), pool_pre_ping=True)
        started = time.perf_counter()
        try:
            with engine.connect() as conn:
                result = conn.execute(text(sql))
                columns = list(result.keys())
                rows = []
                for row in result.fetchmany(limit + 1):
                    rows.append({columns[i]: _convert(value) for i, value in enumerate(row)})
                return columns, rows, round(time.perf_counter() - started, 4)
        finally:
            engine.dispose()

    @staticmethod
    def masked(connection: DatabaseConnection) -> dict[str, Any]:
        return {
            "id": connection.id,
            "name": connection.name,
            "db_type": connection.db_type,
            "host": connection.host,
            "port": connection.port,
            "username": connection.username,
            "database_name": connection.database_name,
            "sqlite_path": connection.sqlite_path,
            "created_at": connection.created_at.isoformat(sep=" ") if connection.created_at else None,
        }


database_service = DatabaseService()
