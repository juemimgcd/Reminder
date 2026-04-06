from sqlalchemy import BigInteger, ForeignKey, Identity, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class Document(Base):
    __tablename__ = "documents"
    __table_args__ = (
        Index("idx_documents_user_id", "user_id"),
        Index("idx_documents_knowledge_base_pk", "knowledge_base_pk"),
        Index("idx_documents_status", "status"),
        Index("idx_documents_user_created_at", "user_id", "created_at"),
        Index("idx_documents_knowledge_base_pk_created_at", "knowledge_base_pk", "created_at"),
    )

    pk: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
        comment="内部主键",
    )
    id: Mapped[str] = mapped_column(String(64), nullable=False, comment="文档公开ID")
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="所属用户ID",
    )
    knowledge_base_id: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="所属知识库公开ID",
    )
    knowledge_base_pk: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("knowledge_bases.pk"),
        nullable=False,
        comment="所属知识库内部主键",
    )
    file_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="原始文件名")
    file_path: Mapped[str] = mapped_column(String(500), nullable=False, comment="文件存储路径")
    file_type: Mapped[str] = mapped_column(String(50), nullable=False, comment="文件类型")
    file_size: Mapped[int] = mapped_column(Integer, nullable=False, comment="文件大小，单位字节")
    status: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        default="uploaded",
        comment="文档状态",
    )

    def __repr__(self) -> str:
        return f"<Document(pk={self.pk}, id={self.id}, file_name='{self.file_name}', status='{self.status}')>"
