from datetime import datetime

from sqlalchemy import BigInteger, Column, DateTime, Float, ForeignKey, Index, String, Table, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    __table_args__ = (
        Index("idx_memory_entries_user_id", "user_id"),
        Index("idx_memory_entries_knowledge_base_pk", "knowledge_base_pk"),
        Index("idx_memory_entries_document_pk", "document_pk"),
        Index("idx_memory_entries_entry_type", "entry_type"),
        Index("idx_memory_entries_chunk_id", "chunk_id"),
        Index("uq_memory_entries_source_fingerprint", "source_fingerprint", unique=True),
        Index("idx_memory_entries_kb_status", "knowledge_base_pk", "status"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    knowledge_base_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_bases.pk"),
        nullable=False,
    )
    document_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    document_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.pk"),
        nullable=False,
    )
    chunk_id: Mapped[str] = mapped_column(String(64), nullable=False)
    entry_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    evidence_text: Mapped[str] = mapped_column(Text, nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    source_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    extraction_version: Mapped[str] = mapped_column(String(32), nullable=False, default="v1")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    confidence: Mapped[float] = mapped_column(Float, nullable=False, default=0.5)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    valid_from: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    valid_to: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CanonicalMemory(Base):
    __tablename__ = "canonical_memories"
    __table_args__ = (
        Index("idx_canonical_memories_kb_status", "knowledge_base_pk", "status"),
        Index("idx_canonical_memories_user_id", "user_id"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    knowledge_base_id: Mapped[str] = mapped_column(String(64), nullable=False)
    knowledge_base_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_bases.pk", ondelete="CASCADE"),
        nullable=False,
    )
    entry_name: Mapped[str] = mapped_column(String(255), nullable=False)
    entry_type: Mapped[str] = mapped_column(String(50), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    representative_entry_id: Mapped[str] = mapped_column(String(64), nullable=False)
    evidence_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    document_count: Mapped[int] = mapped_column(BigInteger, nullable=False)
    importance_score: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


canonical_memory_evidence = Table(
    "canonical_memory_evidence",
    Base.metadata,
    Column(
        "canonical_memory_id",
        String(64),
        ForeignKey("canonical_memories.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "memory_entry_id",
        String(64),
        ForeignKey("memory_entries.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class MemoryRelation(Base):
    __tablename__ = "memory_relations"
    __table_args__ = (Index("idx_memory_relations_knowledge_base_pk", "knowledge_base_pk"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    knowledge_base_id: Mapped[str] = mapped_column(String(64), nullable=False)
    knowledge_base_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_bases.pk", ondelete="CASCADE"),
        nullable=False,
    )
    source_entry_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("memory_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    target_entry_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("memory_entries.id", ondelete="CASCADE"),
        nullable=False,
    )
    relation_type: Mapped[str] = mapped_column(String(32), nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
