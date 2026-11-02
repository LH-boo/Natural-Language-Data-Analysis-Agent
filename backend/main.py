from __future__ import annotations

import time
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from api import analysis, chat, database, dataset
from config import APP_NAME, APP_START_TIME, APP_VERSION, FRONTEND_DIST
from models import init_db

init_db()

app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    description="基于 FastAPI + LangGraph + DuckDB 的自然语言数据分析 Agent",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dataset.router)
app.include_router(database.router)
app.include_router(chat.router)
app.include_router(analysis.router)


@app.get("/api/health", tags=["系统"])
def health():
    return {
        "status": "ok",
        "app": APP_NAME,
        "version": APP_VERSION,
        "uptime_seconds": int(time.time() - APP_START_TIME),
    }


def _index_file() -> Path:
    return FRONTEND_DIST / "index.html"


@app.get("/", include_in_schema=False)
def root():
    index = _index_file()
    if index.is_file():
        return FileResponse(index)
    return {
        "name": APP_NAME,
        "version": APP_VERSION,
        "docs": "/docs",
        "health": "/api/health",
    }


@app.get("/{full_path:path}", include_in_schema=False)
def frontend(full_path: str):
    index = _index_file()
    if not index.is_file():
        raise HTTPException(
            status_code=404,
            detail="前端尚未构建，请先在 frontend 目录执行 npm run build",
        )
    if full_path.startswith(("api/", "docs", "redoc", "openapi.json")):
        raise HTTPException(status_code=404, detail="Not Found")
    dist_root = FRONTEND_DIST.resolve()
    target = (dist_root / full_path).resolve()
    if full_path and target.is_relative_to(dist_root) and target.is_file():
        return FileResponse(target)
    return FileResponse(index)
