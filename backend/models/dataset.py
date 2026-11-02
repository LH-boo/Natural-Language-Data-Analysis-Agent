from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from models.base import Base


def now() -> datetime:
    return datetime.now()


class Dataset(Base):
    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    source_type = Column(String(30), default="csv")
    table_name = Column(String(255), nullable=False)
    file_path = Column(String(500))
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
    row_count = Column(BigInteger, default=0)
    column_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=now)

    columns = relationship(
        "DatasetColumn", back_populates="dataset", cascade="all, delete-orphan", order_by="DatasetColumn.ordinal"
    )


class DatasetColumn(Base):
    __tablename__ = "dataset_columns"

    id = Column(Integer, primary_key=True, autoincrement=True)
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    dtype = Column(String(60), default="object")
    description = Column(String(255), default="")
    missing_count = Column(BigInteger, default=0)
    unique_count = Column(BigInteger, default=0)
    ordinal = Column(Integer, default=0)

    dataset = relationship("Dataset", back_populates="columns")


class DatabaseConnection(Base):
    __tablename__ = "database_connections"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    db_type = Column(String(30), default="mysql")
    host = Column(String(255), default="")
    port = Column(Integer, default=3306)
    username = Column(String(255), default="")
    password = Column(String(500), default="")
    database_name = Column(String(255), default="")
    sqlite_path = Column(String(500), default="")
    created_at = Column(DateTime, default=now)
