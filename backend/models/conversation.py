import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from models.base import Base


def now() -> datetime:
    return datetime.now()


def new_id() -> str:
    return uuid.uuid4().hex


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(String(64), primary_key=True, default=new_id)
    title = Column(String(255), default="新的分析会话")
    dataset_id = Column(Integer, ForeignKey("datasets.id"), nullable=True)
    connection_id = Column(Integer, ForeignKey("database_connections.id"), nullable=True)
    created_at = Column(DateTime, default=now)
    updated_at = Column(DateTime, default=now, onupdate=now)


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True)
    conversation_id = Column(String(64), ForeignKey("conversations.id"), index=True, nullable=False)
    role = Column(String(20), nullable=False)
    content = Column(Text, default="")
    payload_json = Column(Text, default="")
    created_at = Column(DateTime, default=now)
