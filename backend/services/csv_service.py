from __future__ import annotations

import threading
import uuid
from pathlib import Path
from typing import Any, BinaryIO

import duckdb
import pandas as pd
from sqlalchemy.orm import Session

from config import MAX_UPLOAD_MB, SAMPLE_DIR, UPLOAD_DIR
from models import Dataset, DatasetColumn
from services.schema_service import describe_column
from utils.data import df_to_payload, quote_ident

_write_lock = threading.Lock()

ENCODINGS = ("utf-8-sig", "utf-8", "gbk", "gb18030", "latin-1")


def connect(read_only: bool = False):
    from config import DUCKDB_PATH

    return duckdb.connect(DUCKDB_PATH, read_only=read_only)


def read_csv(path: str | Path) -> pd.DataFrame:
    last_error: Exception | None = None
    for encoding in ENCODINGS:
        try:
            return pd.read_csv(path, encoding=encoding, low_memory=False)
        except UnicodeDecodeError as exc:
            last_error = exc
        except pd.errors.EmptyDataError as exc:
            raise ValueError("CSV 文件为空或格式不正确") from exc
    raise ValueError(f"无法识别 CSV 文件编码：{last_error}")


def sanitize_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(column).replace("\ufeff", "").strip() or f"列_{i + 1}" for i, column in enumerate(df.columns)]

    seen: dict[str, int] = {}
    new_columns = []
    for column in df.columns:
        if column in seen:
            seen[column] += 1
            new_columns.append(f"{column}_{seen[column]}")
        else:
            seen[column] = 0
            new_columns.append(column)
    df.columns = new_columns

    for column in df.columns:
        series = df[column]
        if series.dtype == object:
            non_null = series.dropna()
            if non_null.empty:
                continue
            lowered = str(column).lower()
            time_hint = any(token in lowered for token in ("date", "time", "日期", "时间", "月份"))
            parsed_time = pd.to_datetime(series, errors="coerce")
            if time_hint or parsed_time.notna().mean() >= 0.85:
                if parsed_time.notna().mean() >= 0.85 and parsed_time.notna().sum() > 0:
                    df[column] = parsed_time
                    continue
            parsed_number = pd.to_numeric(series, errors="coerce")
            if parsed_number.notna().mean() >= 0.9:
                df[column] = parsed_number

    return df


def _import_to_duckdb(table_name: str, df: pd.DataFrame) -> None:
    with _write_lock:
        conn = connect()
        try:
            conn.register("_incoming_df", df)
            conn.execute(
                f"CREATE OR REPLACE TABLE {quote_ident(table_name)} AS SELECT * FROM _incoming_df"
            )
            conn.unregister("_incoming_df")
        finally:
            conn.close()


def create_dataset(
    session: Session,
    df: pd.DataFrame,
    name: str,
    source_type: str = "csv",
    file_path: str = "",
    connection_id: int | None = None,
) -> Dataset:
    if df.empty:
        raise ValueError("数据为空，无法创建数据集")

    df = sanitize_dataframe(df)
    dataset = Dataset(
        name=name,
        source_type=source_type,
        table_name="pending",
        file_path=file_path,
        connection_id=connection_id,
        row_count=int(len(df)),
        column_count=int(len(df.columns)),
    )
    session.add(dataset)
    session.flush()

    dataset.table_name = f"ds_{dataset.id}"
    _import_to_duckdb(dataset.table_name, df)

    for index, column in enumerate(df.columns):
        series = df[column]
        session.add(
            DatasetColumn(
                dataset_id=dataset.id,
                name=str(column),
                dtype=str(series.dtype),
                description=describe_column(str(column), str(series.dtype)),
                missing_count=int(series.isna().sum()),
                unique_count=int(series.nunique(dropna=True)),
                ordinal=index,
            )
        )
    session.flush()
    session.refresh(dataset)
    return dataset


def create_dataset_from_csv(session: Session, path: str | Path, name: str) -> Dataset:
    df = read_csv(path)
    return create_dataset(session, df, name=name, source_type="csv", file_path=str(path))


def load_sample_dataset(session: Session) -> Dataset:
    path = SAMPLE_DIR / "sales.csv"
    if not path.exists():
        raise ValueError("示例数据文件不存在")
    return create_dataset_from_csv(session, path, name="示例销售数据")


async def save_upload(upload: Any) -> Path:
    filename = Path(upload.filename or "upload.csv").name
    suffix = Path(filename).suffix.lower()
    if suffix not in (".csv", ".txt", ".tsv"):
        raise ValueError("仅支持上传 CSV 文件")

    target = UPLOAD_DIR / f"{uuid.uuid4().hex}{suffix}"
    total = 0
    max_bytes = MAX_UPLOAD_MB * 1024 * 1024
    with target.open("wb") as file:
        while True:
            chunk = await upload.read(1024 * 1024)
            if not chunk:
                break
            total += len(chunk)
            if total > max_bytes:
                file.close()
                target.unlink(missing_ok=True)
                raise ValueError(f"文件大小超过 {MAX_UPLOAD_MB} MB 限制")
            file.write(chunk)
    if total == 0:
        target.unlink(missing_ok=True)
        raise ValueError("上传文件为空")
    return target


def preview(dataset: Dataset, limit: int = 50, offset: int = 0) -> dict[str, Any]:
    sql = f"SELECT * FROM {quote_ident(dataset.table_name)} LIMIT ? OFFSET ?"
    conn = connect()
    try:
        cursor = conn.execute(sql, [int(limit), int(offset)])
        columns = [description[0] for description in cursor.description]
        rows = [dict(zip(columns, row)) for row in cursor.fetchall()]
    finally:
        conn.close()

    payload_columns, payload_rows = df_to_payload(pd.DataFrame(rows, columns=columns))
    return {
        "columns": payload_columns,
        "rows": payload_rows,
        "total": int(dataset.row_count),
        "limit": limit,
        "offset": offset,
    }


def drop_dataset(dataset: Dataset) -> None:
    with _write_lock:
        conn = connect()
        try:
            conn.execute(f"DROP TABLE IF EXISTS {quote_ident(dataset.table_name)}")
        finally:
            conn.close()
    if dataset.file_path:
        path = Path(dataset.file_path)
        if path.exists() and UPLOAD_DIR in path.parents:
            path.unlink(missing_ok=True)


def save_binary(file: BinaryIO, filename: str) -> Path:
    target = UPLOAD_DIR / filename
    with target.open("wb") as output:
        output.write(file.read())
    return target
