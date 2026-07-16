from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    String,
    Table,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.memoria.server.models.base import Base

candidate_evidence = Table(
    "memory_candidate_evidence",
    Base.metadata,
    Column(
        "candidate_id",
        String(64),
        ForeignKey("memory_candidates.candidate_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        String(64),
        ForeignKey("memory_evidence.evidence_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)

revision_evidence = Table(
    "memory_revision_evidence",
    Base.metadata,
    Column(
        "revision_id",
        String(64),
        ForeignKey("memory_revisions.revision_id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "evidence_id",
        String(64),
        ForeignKey("memory_evidence.evidence_id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Evidence(Base):
    __tablename__ = "memory_evidence"
    __table_args__ = (
        Index("ix_memory_evidence_owner_scope", "owner_id", "knowledge_base_id"),
    )

    evidence_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    identity_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    owner_id: Mapped[int] = mapped_column(nullable=False)
    knowledge_base_id: Mapped[str | None] = mapped_column(String(128))
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_id: Mapped[str] = mapped_column(String(128), nullable=False)
    source_document_id: Mapped[str | None] = mapped_column(String(128), index=True)
    source_version: Mapped[str] = mapped_column(String(128), nullable=False)
    minimum_text: Mapped[str] = mapped_column(Text, nullable=False)
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
