import asyncio
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.agent.contracts import AgentRequest, AgentResponse
from app.mneme.agent.events import AgentEvent
from app.mneme.agent.orchestrator import generate_rag_answer
from app.mneme.agent.runner import MnemeAgentRunner
from app.mneme.agent.runtime_context import AgentRunContext
from app.mneme.agent.runtime_events import RuntimeEventDispatcher
from app.mneme.agent.service import MnemeAgent


class RagAnswerEngine:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate(self, request: AgentRequest) -> AgentResponse:
        result = await generate_rag_answer(
            question=request.question,
            db=self.db,
            knowledge_base_id=request.knowledge_base_id,
            user_id=request.user_id,
            top_k=request.top_k,
            answer_mode=request.answer_mode,
            llm_config=request.llm_config,
        )
        return AgentResponse.model_validate(result)


class RuntimeAnswerEngine:
    def __init__(self, db: AsyncSession, runner: MnemeAgentRunner | None = None):
        self.db = db
        self.runner = runner or MnemeAgentRunner()

    async def generate(self, request: AgentRequest) -> AgentResponse:
        context = self._build_context(request, asyncio.Event())
        return await self.runner.run(request, context)

    async def stream(
        self,
        request: AgentRequest,
        *,
        abort_signal: asyncio.Event | None = None,
    ) -> AsyncIterator[AgentEvent]:
        context = self._build_context(request, abort_signal or asyncio.Event())
        async for event in self.runner.stream(request, context):
            yield event

    def _build_context(self, request: AgentRequest, abort_signal: asyncio.Event) -> AgentRunContext:
        runtime_events = RuntimeEventDispatcher(
            trace_id=request.trace_id,
            run_id=request.run_id,
            session_id=request.session_id,
            user_id=request.user_id,
        )
        return AgentRunContext(
            db=self.db,
            user_id=request.user_id,
            knowledge_base_id=request.knowledge_base_id,
            session_id=request.session_id,
            run_id=request.run_id,
            trace_id=request.trace_id,
            llm_config=request.llm_config,
            abort_signal=abort_signal,
            runtime_events=runtime_events,
        )


def build_mneme_agent(db: AsyncSession) -> MnemeAgent:
    return MnemeAgent(answer_engine=RuntimeAnswerEngine(db))
