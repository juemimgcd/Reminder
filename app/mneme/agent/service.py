from app.mneme.agent.contracts import AgentRequest, AgentResponse
from app.mneme.agent.ports import AgentAnswerEngine


class MnemeAgent:
    def __init__(self, answer_engine: AgentAnswerEngine):
        self.answer_engine = answer_engine

    async def run(self, request: AgentRequest) -> AgentResponse:
        return await self.answer_engine.generate(request)
