from typing import Optional

from sqlalchemy import BigInteger, ForeignKey, Identity, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Chunk(Base):
    __tablename__ = "chunks"
    __table_args__ = (
        Index("idx_chunks_document_pk", "document_pk"),
        Index("idx_chunks_document_pk_chunk_index", "document_pk", "chunk_index"),
    )

    pk: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
        comment="内部主键",
    )
    id: Mapped[str] = mapped_column(String(64), nullable=False, comment="Chunk 公开ID")
    document_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="所属文档公开ID",
    )
    document_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("documents.pk"),
        nullable=False,
        comment="所属文档内部主键",
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False, comment="Chunk 顺序号")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="文本块内容")
    page_no: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="页码")
    start_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="起始偏移量")
    end_offset: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, comment="结束偏移量")

    def __repr__(self) -> str:
        return f"<Chunk(pk={self.pk}, id={self.id}, document_id={self.document_id}, chunk_index={self.chunk_index})>"
