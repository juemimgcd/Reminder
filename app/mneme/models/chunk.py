from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("idx_chunks_document_pk", "document_pk"),
        Index("idx_chunks_document_pk_chunk_index", "document_pk", "chunk_index"),
        Index("idx_chunks_document_pk_section_id", "document_pk", "section_id"),
    )

    pk: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
        comment="Internal primary key",
    )
    id: Mapped[str] = mapped_column(String(64), nullable=False, comment="Public chunk ID")
    document_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Owning document public ID",
    )
    document_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.pk"),
        nullable=False,
        comment="Owning document internal primary key",
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="Global chunk order")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="Chunk content")
    page_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Page number")
    start_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="Start offset")
    end_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="End offset")
    section_id: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    section_title: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    section_level: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    section_path: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    section_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    section_chunk_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    def __repr__(self) -> str:
        return (
            f"<Chunk(pk={self.pk}, id={self.id}, "
            f"document_id={self.document_id}, chunk_index={self.chunk_index})>"
        )
