from datetime import UTC, datetime
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from services.memory_agent.contracts.answers import AnswerRequest
from services.memory_agent.database import open_read_session, open_write_session
from services.memory_agent.models.answer_run import AnswerRun
from services.memory_agent.runtime.contracts import AnswerRunData, GeneratedAnswer, RunPhase


class InvalidRunTransition(RuntimeError):
    pass


def _duration(value: int) -> int:
    return max(0, value)


def _data(row: AnswerRun) -> AnswerRunData:
    return AnswerRunData(
        run_id=row.run_id,
        request_id=row.request_id,
        owner_id=row.owner_id,
        knowledge_base_id=row.knowledge_base_id,
        session_id=row.session_id,
        message_id=row.message_id,
        mode=row.mode,  # type: ignore[arg-type]
        status=row.status,  # type: ignore[arg-type]
        current_phase=row.current_phase,  # type: ignore[arg-type]
        phase_durations_ms=dict(row.phase_durations_ms),
        source_ids=list(row.source_ids),
        expansion_count=row.expansion_count,
        confidence=float(row.confidence) if row.confidence is not None else None,
        uncertainty=row.uncertainty,
        insufficient_evidence=row.insufficient_evidence,
        prompt_tokens=row.prompt_tokens,
        completion_tokens=row.completion_tokens,
        total_tokens=row.total_tokens,
        cost=float(row.cost) if row.cost is not None else None,
        error_code=row.error_code,
        created_at=row.created_at,
        started_at=row.started_at,
        retrieval_completed_at=row.retrieval_completed_at,
        generation_completed_at=row.generation_completed_at,
        citations_completed_at=row.citations_completed_at,
        completed_at=row.completed_at,
        failed_at=row.failed_at,
    )


async def _locked(db: AsyncSession, run_id: str) -> AnswerRun:
    row = await db.scalar(select(AnswerRun).where(AnswerRun.run_id == run_id).with_for_update())
    if row is None:
        raise LookupError(f"answer run {run_id} does not exist")
    return row


def _require_running(row: AnswerRun, expected_phase: RunPhase) -> None:
    if row.status != "running" or row.current_phase != expected_phase:
        raise InvalidRunTransition(
            f"answer run {row.run_id} is {row.status}/{row.current_phase}, expected running/{expected_phase}"
        )


class AnswerRunRepository:
    async def create(
        self,
        *,
        run_id: str,
        request: AnswerRequest,
        validation_duration_ms: int,
    ) -> AnswerRunData:
        # The request question and ephemeral model configuration are deliberately not copied.
        row = AnswerRun(
            run_id=run_id,
            request_id=request.request_id,
            owner_id=request.owner_id,
            knowledge_base_id=request.knowledge_base_id,
            session_id=request.session_id,
            message_id=request.message_id,
            mode=request.answer_mode,
            status="running",
            current_phase="validate",
            phase_durations_ms={"validate": _duration(validation_duration_ms)},
            source_ids=[],
            expansion_count=0,
        )
        async with open_write_session() as db:
            db.add(row)
            await db.flush()
            await db.refresh(row)
            return _data(row)

    async def begin_phase(self, run_id: str, *, previous: RunPhase, phase: RunPhase) -> None:
        async with open_write_session() as db:
            row = await _locked(db, run_id)
            _require_running(row, previous)
            row.current_phase = phase

    async def record_retrieval(
        self,
        run_id: str,
        *,
        duration_ms: int,
        source_ids: list[str],
        expansion_count: int,
    ) -> None:
        async with open_write_session() as db:
            row = await _locked(db, run_id)
            _require_running(row, "retrieve")
            row.phase_durations_ms = {
                **row.phase_durations_ms,
                "retrieve": _duration(duration_ms),
            }
            row.source_ids = list(dict.fromkeys(source_ids))
            row.expansion_count = expansion_count
            row.retrieval_completed_at = datetime.now(UTC)

    async def record_generation(
        self,
        run_id: str,
        *,
        duration_ms: int,
        answer: GeneratedAnswer,
    ) -> None:
        async with open_write_session() as db:
            row = await _locked(db, run_id)
            _require_running(row, "generate")
            row.phase_durations_ms = {
                **row.phase_durations_ms,
                "generate": _duration(duration_ms),
            }
            row.confidence = Decimal(str(answer.confidence))
            row.uncertainty = answer.uncertainty
            row.insufficient_evidence = answer.insufficient_evidence
            row.prompt_tokens = answer.prompt_tokens
            row.completion_tokens = answer.completion_tokens
            row.total_tokens = answer.total_tokens
            row.cost = Decimal(str(answer.cost))
            row.generation_completed_at = datetime.now(UTC)

    async def complete(
        self,
        run_id: str,
        *,
        citation_duration_ms: int,
        confidence: float,
        uncertainty: str | None,
        insufficient_evidence: bool,
    ) -> None:
        now = datetime.now(UTC)
        async with open_write_session() as db:
            row = await _locked(db, run_id)
            _require_running(row, "citations")
            row.phase_durations_ms = {
                **row.phase_durations_ms,
                "citations": _duration(citation_duration_ms),
            }
            row.confidence = Decimal(str(confidence))
            row.uncertainty = uncertainty
            row.insufficient_evidence = insufficient_evidence
            row.status = "completed"
            row.current_phase = "complete"
            row.citations_completed_at = now
            row.completed_at = now

    async def fail(
        self,
        run_id: str,
        *,
        phase: RunPhase,
        duration_ms: int,
        error_code: str,
    ) -> None:
        async with open_write_session() as db:
            row = await _locked(db, run_id)
            if row.status != "running":
                return
            row.phase_durations_ms = {
                **row.phase_durations_ms,
                phase: _duration(duration_ms),
            }
            row.current_phase = phase
            row.status = "failed"
            row.error_code = error_code
            row.failed_at = datetime.now(UTC)

    async def get(self, run_id: str) -> AnswerRunData:
        async with open_read_session() as db:
            row = await db.get(AnswerRun, run_id)
            if row is None:
                raise LookupError(f"answer run {run_id} does not exist")
            return _data(row)
