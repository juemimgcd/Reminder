from sqlalchemy import BigInteger, Boolean, ForeignKey, Identity, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        Index("idx_knowledge_bases_user_id", "user_id"),
        Index("idx_knowledge_bases_is_default", "is_default"),
        Index("idx_knowledge_bases_user_created_at", "user_id", "created_at"),
        Index("idx_knowledge_bases_user_is_default", "user_id", "is_default"),
    )

    pk: Mapped[int] = mapped_column(
        BigInteger,
        Identity(always=False),
        primary_key=True,
        comment="internal primary key",
    )
    id: Mapped[str] = mapped_column(String(64), nullable=False, comment="public knowledge base id")
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="owner user id",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="knowledge base name")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="knowledge base description")
    is_default: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="default knowledge base flag",
    )

    def __repr__(self) -> str:
        return f"<KnowledgeBase(pk={self.pk}, id={self.id}, user_id={self.user_id}, name='{self.name}')>"
