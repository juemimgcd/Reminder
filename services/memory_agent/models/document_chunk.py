from typing import Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from services.memory_agent.config import settings
from services.memory_agent.models.base import Base


class DocumentChunk(Base):
    __tablename__ = "document_chunks"
    __table_args__ = (
        UniqueConstraint("projection_id", "chunk_id"),
        UniqueConstraint("projection_id", "chunk_index"),
        Index(
            "uq_document_chunks_active_chunk_id",
            "chunk_id",
            unique=True,
            postgresql_where=text("is_active"),
        ),
        Index(
            "ix_document_chunks_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
        Index(
            "ix_document_chunks_active_scope",
            "owner_id",
            "knowledge_base_id",
            "is_active",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    projection_id: Mapped[str] = mapped_column(
        ForeignKey("document_projections.projection_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    owner_id: Mapped[int] = mapped_column(Integer, nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(128))
    document_id: Mapped[str] = mapped_column(String(128), nullable=False)
    document_version: Mapped[str] = mapped_column(String(128), nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(128), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    page_no: Mapped[int | None] = mapped_column(Integer)
    section_path: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)
    embedding: Mapped[Any] = mapped_column(Vector(settings.EMBEDDING_DIMENSION), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
