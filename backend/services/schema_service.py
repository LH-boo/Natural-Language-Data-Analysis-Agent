from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from models import DatabaseConnection, Dataset

DESCRIPTION_RULES = [
    (("日期", "时间", "date", "time", "month", "月份"), "时间字段"),
    (("商品名称", "产品名称", "product", "商品", "产品"), "商品/产品名称"),
    (("类别", "分类", "category", "type"), "分类维度"),
    (("地区", "区域", "省份", "城市", "region", "province", "city"), "地区维度"),
    (("单价", "价格", "price"), "单价/价格"),
    (("数量", "quantity", "qty"), "数量"),
    (("销售额", "销售金额", "金额", "amount", "sales", "revenue"), "销售额/金额"),
    (("利润", "profit"), "利润"),
    (("成本", "cost"), "成本"),
    (("订单", "order"), "订单标识"),
    (("客户", "customer"), "客户信息"),
    (("库存", "stock"), "库存数量"),
    (("编号", "id", "code"), "唯一标识"),
    (("评分", "score", "rating"), "评分"),
]


def describe_column(name: str, dtype: str) -> str:
    lowered = str(name).lower()
    for keywords, description in DESCRIPTION_RULES:
        if any(keyword in lowered for keyword in keywords):
            return description
    if any(t in str(dtype).lower() for t in ("int", "float", "double", "decimal")):
        return "数值指标"
    return "文本字段"


def dataset_schema(dataset: Dataset) -> dict[str, Any]:
    return {
        "source_type": "dataset",
        "table_name": dataset.table_name,
        "dataset_name": dataset.name,
        "row_count": dataset.row_count,
        "columns": [
            {
                "name": column.name,
                "dtype": column.dtype,
                "description": column.description,
                "missing_count": column.missing_count,
                "unique_count": column.unique_count,
            }
            for column in dataset.columns
        ],
    }


def schema_prompt(schema: dict[str, Any]) -> str:
    if "tables" in schema:
        blocks = []
        for table in schema["tables"]:
            lines = [f"表名：{table['name']}（约 {table.get('row_count', 0)} 行）"]
            for column in table["columns"]:
                lines.append(
                    f"- {column['name']} ({column['dtype']})：{column.get('description', '')}"
                )
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    lines = [f"表名：{schema['table_name']}（约 {schema.get('row_count', 0)} 行）", "字段："]
    for column in schema["columns"]:
        lines.append(f"- {column['name']} ({column['dtype']})：{column.get('description', '')}")
    return "\n".join(lines)


def get_dataset_schema(session: Session, dataset_id: int) -> dict[str, Any]:
    dataset = session.get(Dataset, dataset_id)
    if not dataset:
        raise ValueError("数据集不存在")
    return dataset_schema(dataset)


def get_connection_schema(session: Session, connection_id: int) -> dict[str, Any]:
    from services.database_service import database_service

    connection = session.get(DatabaseConnection, connection_id)
    if not connection:
        raise ValueError("数据库连接不存在")
    return database_service.get_schema(connection)
