import asyncio
import json
import time
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr
from starlette.requests import Request

from app.mneme.bootstrap.app_factory import create_app
from app.mneme.channels.adapters.feishu import FeishuAdapter
from app.mneme.channels.contracts import (
    ChannelDeliveryRequest,
    ChannelGatewayError,
    ChannelPartialDeliveryError,
    OutboundPart,
    PersistedAnswer,
)
from app.mneme.channels.inbound import _conversation_scope_key, _inbound_key
from app.mneme.conf.config import settings
from app.mneme.domains.channels.router import get_channel_configuration_api
from app.mneme.infra.celery_app import celery_app

ROOT = Path(__file__).resolve().parents[1]


def _request() -> Request:
    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/channels/feishu/webhook",
            "headers": [],
        }
    )


def test_channel_configuration_reports_readiness_without_exposing_secrets(
    monkeypatch,
):
    monkeypatch.setattr(settings, "FEISHU_ENABLED", True)
    monkeypatch.setattr(settings, "FEISHU_APP_ID", "cli_a")
    monkeypatch.setattr(settings, "FEISHU_APP_SECRET", SecretStr("secret-a"))
    monkeypatch.setattr(
        settings,
        "FEISHU_VERIFICATION_TOKEN",
        SecretStr("token-a"),
    )

    response = asyncio.run(get_channel_configuration_api(None))
    data = response.data

    assert data.ready is True
    assert data.app_secret_configured is True
    assert data.verification_token_configured is True
    assert "secret-a" not in response.model_dump_json()
    assert "token-a" not in response.model_dump_json()


def _event_payload(*, token: str = "verify-token") -> dict:
    return {
        "schema": "2.0",
        "header": {
            "event_id": "event-1",
            "event_type": "im.message.receive_v1",
            "tenant_key": "tenant-1",
            "token": token,
        },
        "event": {
            "sender": {
                "sender_id": {
                    "open_id": "ou-user-1",
                }
            },
            "message": {
                "message_id": "om-message-1",
                "chat_id": "oc-chat-1",
                "thread_id": "omt-thread-1",
                "message_type": "text",
                "content": json.dumps({"text": "What changed?"}),
            },
        },
    }


def test_feishu_callback_requires_configured_verification_token(monkeypatch):
    monkeypatch.setattr(settings, "FEISHU_ENABLED", True)
    monkeypatch.setattr(
        settings,
        "FEISHU_VERIFICATION_TOKEN",
        SecretStr("verify-token"),
    )
    adapter = FeishuAdapter()

    asyncio.run(adapter.verify_inbound(_request(), _event_payload()))
    with pytest.raises(ChannelGatewayError):
        asyncio.run(
            adapter.verify_inbound(
                _request(),
                _event_payload(token="wrong-token"),
            )
        )
    asyncio.run(adapter._client.aclose())


def test_feishu_message_is_normalized_without_trusting_owner_scope():
    adapter = FeishuAdapter()

    messages = adapter.parse_inbound(_event_payload())

    assert len(messages) == 1
    message = messages[0]
    assert message.channel == "feishu"
    assert message.account_id == "tenant-1"
    assert message.sender_id == "ou-user-1"
    assert message.conversation_id == "oc-chat-1"
    assert message.thread_id == "omt-thread-1"
    assert message.text == "What changed?"
    assert "owner_id" not in message.metadata
    assert "knowledge_base_id" not in message.metadata
    asyncio.run(adapter._client.aclose())


def test_inbound_and_conversation_keys_have_the_required_idempotency_scope():
    adapter = FeishuAdapter()
    first = adapter.parse_inbound(_event_payload())[0]
    duplicate = first.model_copy()
    another_account = first.model_copy(update={"account_id": "tenant-2"})

    assert _inbound_key(first) == _inbound_key(duplicate)
    assert _inbound_key(first) != _inbound_key(another_account)
    assert _conversation_scope_key(first) != _conversation_scope_key(
        first.model_copy(update={"thread_id": "other-thread"})
    )
    asyncio.run(adapter._client.aclose())


def test_feishu_answer_rendering_downgrades_markdown_and_hides_quotes(monkeypatch):
    monkeypatch.setattr(settings, "FEISHU_MAX_TEXT_CHARS", 120)
    adapter = FeishuAdapter()
    answer = PersistedAnswer(
        message_id="message-1",
        run_id="run-1",
        content="# Result\n" + ("Evidence-backed answer. " * 20),
        citations=[
            {
                "document_id": "doc-1",
                "source_type": "document",
                "page_no": 3,
                "quote": "private evidence body",
            }
        ],
    )

    parts = adapter.render_answer(answer)

    assert len(parts) > 1
    assert all(len(part.content) <= 120 for part in parts)
    rendered = "\n".join(part.content for part in parts)
    assert "# Result" not in rendered
    assert "doc-1" in rendered
    assert "private evidence body" not in rendered
    asyncio.run(adapter._client.aclose())


def test_feishu_partial_delivery_reports_resume_cursor():
    calls = 0

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(
                200,
                json={"code": 0, "data": {"message_id": "om-sent-1"}},
            )
        return httpx.Response(503, json={"code": 1, "msg": "unavailable"})

    async def execute():
        adapter = FeishuAdapter()
        await adapter._client.aclose()
        adapter._client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler),
            base_url="https://open.feishu.cn",
        )
        adapter._tenant_token = "tenant-token"
        adapter._tenant_token_expires_at = time.monotonic() + 3600
        try:
            await adapter.send(
                ChannelDeliveryRequest(
                    delivery_id="delivery-1",
                    account_id="tenant-1",
                    conversation_id="oc-chat-1",
                    parts=[
                        OutboundPart(content="first"),
                        OutboundPart(content="second"),
                    ],
                )
            )
        finally:
            await adapter._client.aclose()

    with pytest.raises(ChannelPartialDeliveryError) as captured:
        asyncio.run(execute())

    assert captured.value.sent_count == 1
    assert captured.value.external_message_ids == ["om-sent-1"]
    assert captured.value.retryable is True


def test_channel_routes_and_delivery_tasks_are_registered():
    paths = {route.path for route in create_app().routes}

    assert "/channels/configuration" in paths
    assert "/channels/feishu/webhook" in paths
    assert "/channels/link-codes" in paths
    assert "/channels/conversations/{conversation_id}" in paths
    assert "/channels/deliveries" in paths
    assert "/channels/deliveries/{delivery_id}/retry" in paths
    assert (
        celery_app.conf.task_routes["tasks.process_channel_delivery_task"][
            "queue"
        ]
        == settings.CELERY_CHANNEL_QUEUE
    )
    assert (
        celery_app.conf.task_routes["tasks.process_channel_inbound_task"][
            "queue"
        ]
        == settings.CELERY_CHANNEL_QUEUE
    )
    assert "dispatch-channel-deliveries" in celery_app.conf.beat_schedule


def test_channel_sdk_boundary_stays_outside_memoria_runtime():
    runtime_root = ROOT / "app" / "mneme" / "memoria" / "server"
    combined = "\n".join(
        path.read_text(encoding="utf-8")
        for path in runtime_root.rglob("*.py")
    )

    assert "app.mneme.channels" not in combined
    assert "feishu" not in combined.lower()
