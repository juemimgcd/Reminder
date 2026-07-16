import jwt
from fastapi.testclient import TestClient

from app.mneme.memoria.server.api import answers as answers_api
from app.mneme.memoria.server.app import create_memory_agent_app
from app.mneme.memoria.server.config import settings


def _token(scope: str, *, owner_id: int = 7, knowledge_base_id: str | None = "kb-1") -> str:
    return jwt.encode(
        {
            "iss": "mneme-backend",
            "aud": settings.SERVICE_JWT_AUDIENCE,
            "iat": 1_752_556_800,
            "exp": 4_102_444_800,
            "scope": scope,
            "owner_id": owner_id,
            "knowledge_base_id": knowledge_base_id,
        },
        settings.SERVICE_JWT_SECRET.get_secret_value(),
        algorithm="HS256",
    )


class _FakeAgent:
    async def run(self, request):
        from app.mneme.memoria.server.contracts.answers import AnswerResponse

        return AnswerResponse(
            answer="ok",
            mode=request.answer_mode,
            route=request.answer_mode,
            confidence=0.9,
            run_id="run-1",
        )


def test_answers_requires_service_scope_and_checks_claimed_owner(monkeypatch):
    app = create_memory_agent_app()
    app.dependency_overrides[answers_api.get_memory_agent] = lambda: _FakeAgent()
    with TestClient(app) as client:
        payload = {
            "request_id": "r",
            "owner_id": 7,
            "knowledge_base_id": "kb-1",
            "message_id": "m",
            "question": "q",
            "answer_mode": "kb_qa",
        }
        missing = client.post("/v1/answers", json=payload)
        forbidden = client.post(
            "/v1/answers",
            headers={"Authorization": f"Bearer {_token('answers:write', owner_id=8)}"},
            json=payload,
        )
        success = client.post(
            "/v1/answers",
            headers={"Authorization": f"Bearer {_token('answers:write')}"},
            json=payload,
        )

    assert missing.status_code == 401
    assert forbidden.status_code == 403
    assert success.status_code == 200
    assert success.json()["run_id"] == "run-1"
