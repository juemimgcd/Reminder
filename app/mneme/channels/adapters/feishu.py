import asyncio
import hmac
import json
import re
import time
from typing import Any

import httpx
from fastapi import Request

from app.mneme.channels.contracts import (
    ChannelDeliveryRequest,
    ChannelGatewayError,
    ChannelPartialDeliveryError,
    ChannelSendResult,
    NormalizedAttachment,
    NormalizedInboundMessage,
    OutboundPart,
    PersistedAnswer,
)
from app.mneme.conf.config import settings

_MARKDOWN_LINK = re.compile(r"\[([^\]]+)\]\((https?://[^)]+)\)")
_MARKDOWN_DECORATION = re.compile(r"(?m)^\s{0,3}#{1,6}\s+|[*_~`]{1,3}")


class FeishuAdapter:
    channel = "feishu"

    def __init__(self) -> None:
        self._client = httpx.AsyncClient(
            base_url=settings.FEISHU_API_BASE_URL.rstrip("/"),
            timeout=httpx.Timeout(10.0),
        )
        self._tenant_token = ""
        self._tenant_token_expires_at = 0.0
        self._token_lock = asyncio.Lock()

    async def verify_inbound(
        self,
        request: Request,
        payload: dict[str, Any],
    ) -> None:
        if not settings.FEISHU_ENABLED:
            raise ChannelGatewayError("feishu channel is disabled")
        expected = settings.FEISHU_VERIFICATION_TOKEN.get_secret_value()
        if not expected:
            raise ChannelGatewayError("feishu verification is not configured")
        supplied = _payload_token(payload)
        if not supplied or not hmac.compare_digest(supplied, expected):
            raise ChannelGatewayError("invalid feishu verification token")
        if "encrypt" in payload:
            raise ChannelGatewayError("encrypted feishu callbacks are not enabled")
        # Touch a stable request attribute so verification remains HTTP-bound.
        request.headers.get("x-request-id")

    def parse_inbound(
        self,
        payload: dict[str, Any],
    ) -> list[NormalizedInboundMessage]:
        event = payload.get("event")
        header = payload.get("header")
        if not isinstance(event, dict) or not isinstance(header, dict):
            return []
        message = event.get("message")
        sender = event.get("sender")
        if not isinstance(message, dict) or not isinstance(sender, dict):
            return []
        sender_id = sender.get("sender_id")
        if not isinstance(sender_id, dict):
            return []
        external_sender_id = _first_string(
            sender_id,
            "open_id",
            "union_id",
            "user_id",
        )
        message_id = message.get("message_id")
        conversation_id = message.get("chat_id")
        if not all(
            isinstance(value, str) and value
            for value in (external_sender_id, message_id, conversation_id)
        ):
            return []
        content, attachments = _parse_message_content(message)
        account_id = settings.FEISHU_ACCOUNT_ID
        if account_id == "default":
            account_id = _first_string(header, "tenant_key", "app_id") or "default"
        return [
            NormalizedInboundMessage(
                channel="feishu",
                account_id=account_id,
                conversation_id=conversation_id,
                thread_id=_optional_string(message.get("thread_id")),
                sender_id=external_sender_id,
                message_id=message_id,
                text=content,
                attachments=attachments,
                reply_to_message_id=_optional_string(message.get("parent_id")),
                metadata={
                    "event_id": _optional_string(header.get("event_id")),
                    "message_type": _optional_string(message.get("message_type")),
                    "chat_type": _optional_string(message.get("chat_type")),
                },
            )
        ]

    def render_answer(self, answer: PersistedAnswer) -> list[OutboundPart]:
        text = _plain_text(answer.content)
        references = _citation_summary(answer.citations)
        if references:
            text = f"{text}\n\nReferences\n{references}"
        return [
            OutboundPart(kind="text", content=part)
            for part in _split_text(text, settings.FEISHU_MAX_TEXT_CHARS)
        ]

    async def send(self, delivery: ChannelDeliveryRequest) -> ChannelSendResult:
        sent_ids: list[str] = []
        try:
            token = await self._get_tenant_token()
            for part in delivery.parts:
                sent_ids.append(
                    await self._send_text_part(
                        delivery,
                        part,
                        token=token,
                    )
                )
        except ChannelGatewayError as exc:
            raise ChannelPartialDeliveryError(
                str(exc),
                sent_count=len(sent_ids),
                external_message_ids=sent_ids,
                retryable=exc.retryable,
            ) from exc
        except (httpx.TimeoutException, httpx.NetworkError) as exc:
            raise ChannelPartialDeliveryError(
                "feishu transport unavailable",
                sent_count=len(sent_ids),
                external_message_ids=sent_ids,
                retryable=True,
            ) from exc
        return ChannelSendResult(
            sent_count=len(sent_ids),
            external_message_ids=sent_ids,
        )

    async def _get_tenant_token(self) -> str:
        if self._tenant_token and self._tenant_token_expires_at > time.monotonic() + 60:
            return self._tenant_token
        async with self._token_lock:
            if self._tenant_token and self._tenant_token_expires_at > time.monotonic() + 60:
                return self._tenant_token
            app_secret = settings.FEISHU_APP_SECRET.get_secret_value()
            if not settings.FEISHU_APP_ID or not app_secret:
                raise ChannelGatewayError("feishu credentials are not configured")
            response = await self._client.post(
                "/open-apis/auth/v3/tenant_access_token/internal",
                json={
                    "app_id": settings.FEISHU_APP_ID,
                    "app_secret": app_secret,
                },
            )
            payload = _response_payload(response)
            token = payload.get("tenant_access_token")
            if not isinstance(token, str) or not token:
                raise ChannelGatewayError(
                    "feishu token response was invalid",
                    retryable=response.status_code >= 500,
                )
            self._tenant_token = token
            self._tenant_token_expires_at = time.monotonic() + int(
                payload.get("expire") or 7200
            )
            return token

    async def _send_text_part(
        self,
        delivery: ChannelDeliveryRequest,
        part: OutboundPart,
        *,
        token: str,
    ) -> str:
        body = {
            "msg_type": "text",
            "content": json.dumps({"text": part.content}, ensure_ascii=False),
        }
        headers = {"Authorization": f"Bearer {token}"}
        if delivery.reply_to_message_id:
            response = await self._client.post(
                f"/open-apis/im/v1/messages/{delivery.reply_to_message_id}/reply",
                headers=headers,
                json=body,
            )
        else:
            response = await self._client.post(
                "/open-apis/im/v1/messages",
                params={"receive_id_type": "chat_id"},
                headers=headers,
                json={"receive_id": delivery.conversation_id, **body},
            )
        payload = _response_payload(response)
        data = payload.get("data")
        message_id = data.get("message_id") if isinstance(data, dict) else None
        if not isinstance(message_id, str) or not message_id:
            raise ChannelGatewayError(
                "feishu message delivery failed",
                retryable=response.status_code == 429 or response.status_code >= 500,
            )
        return message_id


def _payload_token(payload: dict[str, Any]) -> str | None:
    header = payload.get("header")
    if isinstance(header, dict):
        token = header.get("token")
        if isinstance(token, str):
            return token
    token = payload.get("token")
    return token if isinstance(token, str) else None


def _response_payload(response: httpx.Response) -> dict[str, Any]:
    try:
        payload = response.json()
    except ValueError as exc:
        raise ChannelGatewayError(
            "feishu returned an invalid response",
            retryable=response.status_code >= 500,
        ) from exc
    if not isinstance(payload, dict) or response.is_error or payload.get("code", 0) != 0:
        raise ChannelGatewayError(
            "feishu API rejected the request",
            retryable=response.status_code == 429 or response.status_code >= 500,
        )
    return payload


def _parse_message_content(
    message: dict[str, Any],
) -> tuple[str, list[NormalizedAttachment]]:
    raw_content = message.get("content")
    if not isinstance(raw_content, str):
        return "", []
    try:
        content = json.loads(raw_content)
    except json.JSONDecodeError:
        return raw_content[:20_000], []
    if not isinstance(content, dict):
        return "", []
    text = content.get("text")
    if isinstance(text, str):
        return text.strip()[:20_000], []
    attachments: list[NormalizedAttachment] = []
    for key, attachment_type in (
        ("file_key", "file"),
        ("image_key", "image"),
        ("audio_key", "audio"),
        ("media_key", "media"),
    ):
        value = content.get(key)
        if isinstance(value, str) and value:
            attachments.append(
                NormalizedAttachment(
                    attachment_type=attachment_type,
                    external_key=value,
                    name=_optional_string(content.get("file_name")),
                )
            )
    fallback = "\n".join(
        f"[{item.attachment_type} attachment: {item.name or item.external_key}]"
        for item in attachments
    )
    return fallback[:20_000], attachments


def _plain_text(value: str) -> str:
    value = _MARKDOWN_LINK.sub(r"\1 (\2)", value)
    value = _MARKDOWN_DECORATION.sub("", value)
    return value.strip() or "The answer was completed without displayable text."


def _citation_summary(citations: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for index, citation in enumerate(citations[:20], start=1):
        source_type = str(citation.get("source_type") or "source")
        source_id = str(
            citation.get("document_id")
            or citation.get("source_id")
            or citation.get("evidence_id")
            or ""
        )
        page = citation.get("page_no")
        suffix = f", page {page}" if isinstance(page, int) else ""
        lines.append(f"[{index}] {source_type}: {source_id or 'available in Mneme'}{suffix}")
    return "\n".join(lines)


def _split_text(value: str, limit: int) -> list[str]:
    if limit < 100:
        raise ValueError("channel text limit is too small")
    parts: list[str] = []
    remaining = value
    while len(remaining) > limit:
        split_at = remaining.rfind("\n", 0, limit + 1)
        if split_at < limit // 2:
            split_at = remaining.rfind(" ", 0, limit + 1)
        if split_at < limit // 2:
            split_at = limit
        parts.append(remaining[:split_at].strip())
        remaining = remaining[split_at:].strip()
    if remaining:
        parts.append(remaining)
    return parts or ["No displayable content."]


def _first_string(values: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = values.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def _optional_string(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
