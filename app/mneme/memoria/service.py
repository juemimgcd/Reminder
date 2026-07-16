import asyncio
from collections.abc import AsyncIterator

from app.mneme.memoria.contracts import AgentRequest, AgentResponse
from app.mneme.memoria.events import AgentEvent
from app.mneme.memoria.ports import AgentAnswerEngine


class MemoriaAgent:
    def __init__(self, answer_engine: AgentAnswerEngine):
        self.answer_engine = answer_engine

    async def run(self, request: AgentRequest) -> AgentResponse:
        return await self.answer_engine.generate(request)

    async def stream(
        self,
        request: AgentRequest,
        *,
        abort_signal: asyncio.Event | None = None,
    ) -> AsyncIterator[AgentEvent]:
        stream_method = getattr(self.answer_engine, "stream", None)
        if stream_method is not None:
            async for event in stream_method(request, abort_signal=abort_signal):
                yield event
            return

        yield AgentEvent.lifecycle("start", loop_index=0)
        response = await self.run(request)
        yield AgentEvent.assistant_delta(response.answer, loop_index=0)
        yield AgentEvent.lifecycle("end", loop_index=0, response=response.model_dump())
