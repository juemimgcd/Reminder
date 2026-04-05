from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base


class KnowledgeBase(Base):
    __tablename__ = "knowledge_bases"
    __table_args__ = (
        Index("idx_knowledge_bases_user_id", "user_id"),
        Index("idx_knowledge_bases_is_default", "is_default"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="知识库ID")
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id"),
        nullable=False,
        comment="所属用户ID",
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, comment="知识库名称")
    description: Mapped[str | None] = mapped_column(Text, nullable=True, comment="知识库描述")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, comment="是否默认知识库")

    def __repr__(self) -> str:
        return f"<KnowledgeBase(id={self.id}, user_id={self.user_id}, name='{self.name}')>"
