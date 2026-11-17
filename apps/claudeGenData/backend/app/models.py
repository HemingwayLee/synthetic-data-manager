from datetime import datetime
from typing import Any

from sqlalchemy import JSON, BigInteger, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Conversation(Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="New chat")
    model: Mapped[str] = mapped_column(String(100))
    # Claude Code session id, used to resume the agent's context on the next turn.
    claude_session_id: Mapped[str | None] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    messages: Mapped[list["Message"]] = relationship(
        back_populates="conversation", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"))
    role: Mapped[str] = mapped_column(String(20))  # "user" | "assistant"
    # Ordered content blocks: {"type": "text"|"tool_use"|"tool_result"|"error", ...}
    blocks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, default=list)
    cost_usd: Mapped[float | None]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    conversation: Mapped[Conversation] = relationship(back_populates="messages")


class BizDocBatch(Base):
    """Documents queued together by Batch Generation; archived once all of them finish (see bizdoc/batches.py)."""

    __tablename__ = "bizdoc_batches"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_type: Mapped[str] = mapped_column(String(50))
    count: Mapped[int]
    status: Mapped[str] = mapped_column(String(20), default="generating")  # generating | archiving | done | empty | failed
    # Timestamp of the batch's archive, exports/<export>.tar.gz.
    export: Mapped[int | None] = mapped_column(BigInteger)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GeneratedDocument(Base):
    __tablename__ = "generated_documents"

    id: Mapped[int] = mapped_column(primary_key=True)
    doc_type: Mapped[str] = mapped_column(String(50), index=True)
    status: Mapped[str] = mapped_column(String(20), default="queued")  # queued | running | done | failed | cancelled
    # Set for documents queued by Batch Generation. Added to existing databases by bizdoc.batches.migrate().
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("bizdoc_batches.id", ondelete="SET NULL"), index=True)
    model: Mapped[str] = mapped_column(String(100))
    # Settings with every "random" choice resolved, i.e. what this document was generated from.
    settings: Mapped[dict[str, Any]] = mapped_column(JSON)
    title: Mapped[str | None] = mapped_column(String(300))
    labels: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
