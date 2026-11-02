from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from models import DatabaseConnection
from models.base import session_scope
from services.database_service import database_service

router = APIRouter(prefix="/api/database", tags=["数据库连接"])


class DatabaseConfig(BaseModel):
    name: str = Field(default="业务数据库", max_length=100)
    db_type: str = "mysql"
    host: str = "127.0.0.1"
    port: int = 3306
    username: str = ""
    password: str = ""
    database_name: str = ""
    sqlite_path: str = ""


@router.post("/test")
def test_connection(config: DatabaseConfig):
    try:
        result = database_service.test(config.model_dump())
        return {"success": True, "message": result["message"]}
    except Exception as exc:
        return {"success": False, "message": f"连接失败：{exc}"}


@router.post("/connect")
def create_connection(config: DatabaseConfig):
    try:
        database_service.test(config.model_dump())
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"连接失败：{exc}") from exc

    with session_scope() as session:
        connection = DatabaseConnection(
            name=config.name,
            db_type=config.db_type,
            host=config.host,
            port=config.port,
            username=config.username,
            password=database_service.encode_password(config.password),
            database_name=config.database_name,
            sqlite_path=config.sqlite_path,
        )
        session.add(connection)
        session.flush()
        return {"success": True, "connection": database_service.masked(connection)}


@router.get("/list")
def list_connections():
    with session_scope() as session:
        connections = session.query(DatabaseConnection).order_by(DatabaseConnection.id.desc()).all()
        return {"items": [database_service.masked(connection) for connection in connections]}


@router.get("/schema")
def get_schema(id: int = Query(...)):
    with session_scope() as session:
        connection = session.get(DatabaseConnection, id)
        if not connection:
            raise HTTPException(status_code=404, detail="数据库连接不存在")
        try:
            return database_service.get_schema(connection)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"读取表结构失败：{exc}") from exc


@router.delete("/{connection_id}")
def delete_connection(connection_id: int):
    with session_scope() as session:
        connection = session.get(DatabaseConnection, connection_id)
        if not connection:
            raise HTTPException(status_code=404, detail="数据库连接不存在")
        session.delete(connection)
    return {"success": True, "message": "数据库连接已删除"}
