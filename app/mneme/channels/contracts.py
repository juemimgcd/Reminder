from datetime import datetime
from typing import Any, Literal, Protocol

from fastapi import Request
from pydantic import BaseModel, Field

from app.mneme.memoria.contracts import AnswerMode

ChannelName = Literal["feishu"]


class NormalizedAttachment(BaseModel):
    attachment_type: str
    external_key: str | None = None
    name: str | None = None
    mime_type: str | None = None
    size: int | None = Field(default=None, ge=0)


class NormalizedInboundMessage(BaseModel):
    channel: ChannelName
    account_id: str = Field(min_length=1, max_length=128)
    conversation_id: str = Field(min_length=1, max_length=128)
    thread_id: str | None = Field(default=None, max_length=128)
    sender_id: str = Field(min_length=1, max_length=128)
    message_id: str = Field(min_length=1, max_length=128)
    text: str = Field(default="", max_length=20_000)
    attachments: list[NormalizedAttachment] = Field(default_factory=list, max_length=20)
    reply_to_message_id: str | None = Field(default=None, max_length=128)
    metadata: dict[str, Any] = Field(default_factory=dict)


class OutboundPart(BaseModel):
    kind: Literal["text", "attachment_notice"] = "text"
    content: str = Field(min_length=1, max_length=20_000)


class PersistedAnswer(BaseModel):
    message_id: str
    run_id: str
    content: str
    citations: list[dict[str, Any]] = Field(default_factory=list)


class ChannelDeliveryRequest(BaseModel):
    delivery_id: str
    account_id: str
    conversation_id: str
    thread_id: str | None = None
    reply_to_message_id: str | None = None
    parts: list[OutboundPart]


class ChannelSendResult(BaseModel):
    sent_count: int = Field(ge=0)
    external_message_ids: list[str] = Field(default_factory=list)


class ChannelAdapter(Protocol):
    channel: ChannelName

    async def verify_inbound(
        self,
        request: Request,
        payload: dict[str, Any],
    ) -> None: ...

    def parse_inbound(
        self,
        payload: dict[str, Any],
    ) -> list[NormalizedInboundMessage]: ...

    async def send(self, delivery: ChannelDeliveryRequest) -> ChannelSendResult: ...

    def render_answer(self, answer: PersistedAnswer) -> list[OutboundPart]: ...


class ChannelLinkCodeCreateRequest(BaseModel):
    channel: ChannelName
    account_id: str = Field(min_length=1, max_length=128)


class ChannelGatewayConfigurationData(BaseModel):
    channel: ChannelName
    enabled: bool
    ready: bool
    account_id: str
    app_id_configured: bool
    app_secret_configured: bool
    verification_token_configured: bool
    callback_path: str
    delivery_queue: str
    max_text_chars: int


class ChannelLinkCodeData(BaseModel):
    channel: ChannelName
    account_id: str
    code: str
    expires_at: datetime
    binding_command: str


class ChannelIdentityData(BaseModel):
    id: str
    channel: str
    account_id: str
    external_user_id: str
    verified_at: datetime
    status: str


class ChannelConversationData(BaseModel):
    id: str
    channel: str
    account_id: str
    external_conversation_id: str
    external_thread_id: str | None
    chat_session_id: str
    knowledge_base_id: str | None
    answer_mode: AnswerMode


class ChannelConversationUpdateRequest(BaseModel):
    chat_session_id: str | None = Field(default=None, max_length=64)
    knowledge_base_id: str | None = None
    answer_mode: AnswerMode = "general_chat"


class ChannelDeliveryData(BaseModel):
    id: str
    channel: str
    agent_run_id: str | None
    assistant_message_id: str | None
    status: str
    parts_sent: int
    part_count: int
    attempt_count: int
    next_attempt_at: datetime | None
    processed_at: datetime | None
    last_error: str | None


class ChannelInboundReceipt(BaseModel):
    message_id: str
    status: Literal["accepted", "bound", "rejected", "submitted", "duplicate"]
    run_id: str | None = None
    code: str | None = None


class ChannelWebhookReceipt(BaseModel):
    accepted: int
    receipts: list[ChannelInboundReceipt]


class ChannelGatewayError(RuntimeError):
    def __init__(self, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.retryable = retryable


class ChannelPartialDeliveryError(ChannelGatewayError):
    def __init__(
        self,
        message: str,
        *,
        sent_count: int,
        external_message_ids: list[str],
        retryable: bool,
    ) -> None:
        super().__init__(message, retryable=retryable)
        self.sent_count = sent_count
        self.external_message_ids = external_message_ids
