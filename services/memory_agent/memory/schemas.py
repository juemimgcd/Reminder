from datetime import datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    model_validator,
)

from services.memory_agent.models.memory_candidate import MemoryType

MAX_EXCERPT_LENGTH = 20_000
MAX_EXTRACTED_CANDIDATES = 8

SensitivitySignal = Literal[
    "identity",
    "health",
    "finance",
    "authentication",
    "credential",
    "secret",
    "password",
    "api_key",
    "token",
    "access_token",
    "refresh_token",
    "auth_token",
    "client_secret",
    "private_key",
    "other_sensitive",
]


class EvidenceInput(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")

    source_type: Literal["document", "conversation", "explicit_request"]
    source_id: str = Field(min_length=1, max_length=128)
    source_version: str = Field(min_length=1, max_length=128)
    excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT_LENGTH)
    occurred_at: datetime


class TemporalHints(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    is_current: StrictBool | None
    valid_from: str | None = Field(max_length=128)
    valid_to: str | None = Field(max_length=128)


class ExtractedCandidate(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid", populate_by_name=True)

    memory_type: MemoryType = Field(alias="type")
    subject: str = Field(min_length=1, max_length=1000)
    predicate: str = Field(min_length=1, max_length=1000)
    value: str = Field(min_length=1, max_length=4000)
    confidence: StrictFloat = Field(ge=0, le=1)
    sensitivity_signals: list[SensitivitySignal] = Field(max_length=8)
    evidence_quote: str = Field(min_length=1, max_length=4000)
    evidence_start: StrictInt = Field(ge=0)
    evidence_end: StrictInt = Field(gt=0)
    temporal_hints: TemporalHints

    def validate_evidence(self, excerpt: str) -> None:
        if self.evidence_end > len(excerpt):
            raise ValueError("evidence boundaries exceed excerpt")
        if excerpt[self.evidence_start : self.evidence_end] != self.evidence_quote:
            raise ValueError("evidence quote does not match excerpt boundaries")
        if self.evidence_quote not in excerpt:
            raise ValueError("evidence quote is not present in excerpt")


class ExtractionResponse(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    candidates: list[ExtractedCandidate] = Field(max_length=MAX_EXTRACTED_CANDIDATES)


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=64)
    content: str = Field(min_length=1, max_length=MAX_EXCERPT_LENGTH)
    created_at: datetime


class ConversationCompletedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1, max_length=64)
    user_message: ConversationMessage
    assistant_message: ConversationMessage

    @model_validator(mode="after")
    def messages_must_be_distinct(self) -> "ConversationCompletedPayload":
        if self.user_message.id == self.assistant_message.id:
            raise ValueError("conversation message IDs must be distinct")
        return self


class MemoryRequestedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    session_id: str = Field(min_length=1, max_length=64)
    message_id: str = Field(min_length=1, max_length=64)
    message_created_at: datetime
    excerpt: str = Field(min_length=1, max_length=MAX_EXCERPT_LENGTH)


class MemorySettingsChangedPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    automatic_conversation_memory: bool
