from sqlalchemy import BigInteger, ForeignKey, Identity, Index, Integer, String, text
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("idx_documents_user_id", "user_id"),
        Index("idx_documents_knowledge_base_pk", "knowledge_base_pk"),
        Index("idx_documents_status", "status"),
        Index("idx_documents_user_created_at", "user_id", "created_at"),
        Index("idx_documents_knowledge_base_pk_created_at", "knowledge_base_pk", "created_at"),
        Index(
            "uq_documents_kb_canonical_sha256",
            "knowledge_base_pk",
            "content_sha256",
            unique=True,
            postgresql_where=text("content_sha256 IS NOT NULL AND duplicate_of_document_id IS NULL"),
        ),
    )

    pk: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
        comment="Internal primary key",
    )
    id: Mapped[str] = mapped_column(String(64), nullable=False, comment="Public document ID")
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="Owner user ID",
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Owning knowledge base public ID",
    )
    knowledge_base_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_bases.pk"),
        nullable=False,
        comment="Owning knowledge base internal primary key",
    )
    folder_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document_folders.pk"),
        nullable=False,
    )
    content_sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)
    normalized_file_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    version_group_id: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    version_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    previous_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    duplicate_of_document_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="Original file name")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="Stored file path")
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="File type")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="File size in bytes")
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="uploaded",
        comment="Document status",
    )

    def __repr__(self) -> str:
        return f"<Document(pk={self.pk}, id={self.id}, file_name='{self.file_name}', status='{self.status}')>"
