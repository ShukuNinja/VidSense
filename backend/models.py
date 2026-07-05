import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from backend.database import Base


def utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    email = Column(String, unique=True, nullable=False, index=True)
    password_hash = Column(String, nullable=False)
    created_at = Column(DateTime, default=utcnow)

    chats = relationship(
        "Chat", back_populates="user", cascade="all, delete-orphan"
    )


class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True)
    user_id = Column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title = Column(String, nullable=False, default="New chat")
    source_url = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)

    video_title = Column(String, nullable=True)
    index_path = Column(String, nullable=True)
    chunk_path = Column(String, nullable=True)

    # pending -> ingesting -> ready | failed
    status = Column(String, nullable=False, default="pending")
    error = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)
    updated_at = Column(DateTime, default=utcnow, onupdate=utcnow)

    user = relationship("User", back_populates="chats")
    messages = relationship(
        "Message",
        back_populates="chat",
        cascade="all, delete-orphan",
        order_by="Message.id",
    )


class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True)
    chat_id = Column(
        Integer, ForeignKey("chats.id", ondelete="CASCADE"), nullable=False, index=True
    )
    role = Column(String, nullable=False)  # user | assistant
    content = Column(Text, nullable=False)

    # On assistant messages: did this turn use conversation history (follow-up)?
    is_followup = Column(Boolean, nullable=True)
    # On assistant messages: JSON citation list (region id + clip-relative span).
    evidence_json = Column(Text, nullable=True)

    created_at = Column(DateTime, default=utcnow)

    chat = relationship("Chat", back_populates="messages")
