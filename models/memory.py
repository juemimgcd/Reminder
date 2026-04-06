from sqlalchemy import BigInteger, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class MemoryEntry(Base):
    __tablename__ = "memory_entries"
    __table_args__ = (
        Index("idx_memory_entries_user_id", "user_id"),
        Index("idx_memory_entries_knowledge_base_pk", "knowledge_base_pk"),
        Index("idx_memory_entries_document_pk", "document_pk"),
        Index("idx_memory_entries_entry_type", "entry_type"),
        Index("idx_memory_entries_chunk_id", "chunk_id"),
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
