from sqlalchemy import BigInteger, Boolean, ForeignKey, Identity, Index, String, UniqueConstraint, text
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class DocumentFolder(Base):
    __tablename__ = "document_folders"
    __table_args__ = (
        UniqueConstraint(
            "knowledge_base_pk",
            "parent_pk",
            "normalized_name",
            name="uq_document_folders_parent_name",
        ),
        Index("idx_document_folders_kb_parent", "knowledge_base_pk", "parent_pk"),
        Index(
            "uq_document_folders_kb_root",
            "knowledge_base_pk",
            unique=True,
            postgresql_where=text("is_root"),
        ),
    )

    pk: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    id: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False)
    knowledge_base_id: Mapped[str] = mapped_column(String(64), nullable=False)
    knowledge_base_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_bases.pk"),
        nullable=False,
    )
    parent_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("document_folders.pk", deferrable=True, initially="DEFERRED"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_root: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
