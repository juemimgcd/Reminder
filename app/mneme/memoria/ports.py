from typing import Protocol

from app.mneme.memoria.contracts import AgentRequest, AgentResponse


class AgentAnswerEngine(Protocol):
    async def generate(self, request: AgentRequest) -> AgentResponse: ...
