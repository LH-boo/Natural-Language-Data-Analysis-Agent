import math
from datetime import date, datetime, time
from decimal import Decimal

import numpy as np
import pandas as pd


def quote_ident(name: str) -> str:
    return '"' + str(name).replace('"', '""') + '"'


def _convert(value):
    if value is None:
        return None
    if isinstance(value, float) and (math.isnan(value) or math.isinf(value)):
        return None
    if isinstance(value, (np.integer,)):
        return int(value)
    if isinstance(value, (np.floating,)):
        value = float(value)
        return None if math.isnan(value) else value
    if isinstance(value, (np.bool_,)):
        return bool(value)
    if value is pd.NaT:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, (pd.Timestamp, datetime, date, time)):
        return value.isoformat(sep=" ") if isinstance(value, (pd.Timestamp, datetime)) else value.isoformat()
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, np.ndarray):
        return [_convert(v) for v in value.tolist()]
    return value


def records_to_json(df: pd.DataFrame) -> list[dict]:
    return [{str(k): _convert(v) for k, v in row.items()} for row in df.to_dict(orient="records")]


def df_to_payload(df: pd.DataFrame) -> tuple[list[str], list[dict]]:
    columns = [str(c) for c in df.columns]
    return columns, records_to_json(df)
