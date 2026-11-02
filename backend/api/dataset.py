from __future__ import annotations

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from api.serializers import dataset_dict
from models import Dataset
from models.base import session_scope
from services import csv_service

router = APIRouter(prefix="/api/dataset", tags=["数据集"])


@router.get("/list")
def list_datasets():
    with session_scope() as session:
        datasets = session.query(Dataset).order_by(Dataset.id.desc()).all()
        return {"items": [dataset_dict(dataset) for dataset in datasets]}


@router.post("/upload")
async def upload_dataset(file: UploadFile = File(...)):
    try:
        path = await csv_service.save_upload(file)
        name = (file.filename or "未命名数据集").rsplit(".", 1)[0]
        with session_scope() as session:
            dataset = csv_service.create_dataset_from_csv(session, path, name=name)
            return {"success": True, "dataset": dataset_dict(dataset, include_columns=True)}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"数据集导入失败：{exc}") from exc


@router.post("/sample")
def create_sample_dataset():
    try:
        with session_scope() as session:
            dataset = csv_service.load_sample_dataset(session)
            return {"success": True, "dataset": dataset_dict(dataset, include_columns=True)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"示例数据加载失败：{exc}") from exc


@router.get("/preview")
def preview_dataset(
    id: int = Query(...),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    with session_scope() as session:
        dataset = session.get(Dataset, id)
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")
        try:
            result = csv_service.preview(dataset, limit=limit, offset=offset)
        except Exception as exc:
            raise HTTPException(status_code=500, detail=f"数据预览失败：{exc}") from exc
        return {
            "dataset": dataset_dict(dataset, include_columns=True),
            **result,
        }


@router.get("/{dataset_id}/schema")
def dataset_schema(dataset_id: int):
    from services.schema_service import get_dataset_schema

    with session_scope() as session:
        try:
            return get_dataset_schema(session, dataset_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.delete("/{dataset_id}")
def delete_dataset(dataset_id: int):
    with session_scope() as session:
        dataset = session.get(Dataset, dataset_id)
        if not dataset:
            raise HTTPException(status_code=404, detail="数据集不存在")
        try:
            csv_service.drop_dataset(dataset)
        except Exception:
            pass
        session.delete(dataset)
    return {"success": True, "message": "数据集已删除"}
