from sqlalchemy import BigInteger, Boolean, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.mneme.models.base import Base


class AiModelConfig(Base):
    __tablename__ = "ai_model_configs"
    __table_args__ = (
        Index("idx_ai_model_configs_user_id", "user_id"),
        Index("idx_ai_model_configs_user_default", "user_id", "is_default"),
    )

    id: Mapped[str] = mapped_column(String(64), primary_key=True, comment="model config id")
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id"), nullable=False, comment="owner user id")
    label: Mapped[str] = mapped_column(String(120), nullable=False, comment="display label")
    provider: Mapped[str] = mapped_column(String(64), nullable=False, comment="provider key")
    base_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="OpenAI-compatible base URL")
    model_name: Mapped[str] = mapped_column(String(255), nullable=False, comment="model name")
    api_key_ciphertext: Mapped[str | None] = mapped_column(Text, nullable=True, comment="encrypted API key")
    temperature: Mapped[float] = mapped_column(Float, nullable=False, default=0.0, server_default="0")
    context_window: Mapped[int] = mapped_column(Integer, nullable=False, default=64000, server_default="64000")
    is_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, server_default="false")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    @property
    def has_api_key(self) -> bool:
        return bool(self.api_key_ciphertext)
