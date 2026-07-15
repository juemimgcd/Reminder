import asyncio
import logging
from dataclasses import dataclass
from time import perf_counter
from uuid import uuid4

from services.memory_agent.contracts.answers import AnswerRequest, AnswerResponse
from services.memory_agent.observability.context import observation_context, safe_log
from services.memory_agent.repositories.runs import AnswerRunRepository
from services.memory_agent.retrieval.contracts import RetrievedEvidence
from services.memory_agent.runtime.contracts import (
    AnswerRunData,
    GenerationRequest,
    RetrievalPlan,
    RunPhase,
    retrieval_request,
)
from services.memory_agent.runtime.plans import MODE_PLANS
from services.memory_agent.runtime.ports import AnswerGenerator, CitationValidator, EvidenceRetriever

POSTGRES_INTEGER_MAX = 2_147_483_647
logger = logging.getLogger(__name__)
DEPENDENCY_ERROR_CODES = {
    "retrieve": frozenset(
        {
            "AGENT_RETRIEVAL_TIMEOUT",
            "AGENT_RETRIEVAL_UNAVAILABLE",
            "AGENT_UNAVAILABLE",
            "AGENT_CAPACITY_EXCEEDED",
        }
    ),
    "generate": frozenset(
        {
            "AGENT_MODEL_TIMEOUT",
            "AGENT_MODEL_UNAVAILABLE",
            "AGENT_UNAVAILABLE",
            "AGENT_CAPACITY_EXCEEDED",
        }
    ),
    "citations": frozenset(
        {
            "AGENT_CITATION_TIMEOUT",
            "AGENT_CITATION_UNAVAILABLE",
            "AGENT_UNAVAILABLE",
            "AGENT_CAPACITY_EXCEEDED",
        }
    ),
}
DEFAULT_PHASE_ERROR_CODES = {
    "retrieve": "AGENT_RETRIEVAL_FAILED",
    "generate": "AGENT_MODEL_FAILED",
    "citations": "AGENT_CITATION_FAILED",
}


@dataclass(frozen=True)
class PhaseTimeouts:
    validate: float = 2.0
    retrieve: float = 20.0
    generate: float = 90.0
    citations: float = 5.0


class RuntimeDependencyError(RuntimeError):
    """A port may raise this to expose a stable, content-free failure code."""

    def __init__(self, error_code: str) -> None:
        super().__init__(error_code)
        self.error_code = error_code


class AnswerRunExecutionError(RuntimeError):
    def __init__(self, *, run_id: str, error_code: str) -> None:
        super().__init__(error_code)
        self.run_id = run_id
        self.error_code = error_code


def _elapsed_ms(started: float) -> int:
    return max(0, round((perf_counter() - started) * 1000))


def _dependency_error_code(exc: Exception, phase: RunPhase) -> str:
    default = DEFAULT_PHASE_ERROR_CODES[phase]
    if not isinstance(exc, RuntimeDependencyError):
        return default
    code = exc.error_code
    if isinstance(code, str) and len(code) <= 64 and code in DEPENDENCY_ERROR_CODES[phase]:
        return code
    return default


def _validate_request(request: AnswerRequest) -> RetrievalPlan:
    # Pydantic validates the mode; this explicit lookup preserves the selected mode verbatim.
    plan = MODE_PLANS.get(request.answer_mode)
    if plan is None:
        raise ValueError("unsupported answer mode")
    if not 1 <= request.owner_id <= POSTGRES_INTEGER_MAX:
        raise ValueError("owner_id is outside the supported range")
    if plan.document and request.knowledge_base_id is None:
        raise ValueError("document retrieval requires a knowledge_base_id")
    identifiers = {
        "request_id": (request.request_id, 128),
        "message_id": (request.message_id, 128),
    }
    if request.knowledge_base_id is not None:
        identifiers["knowledge_base_id"] = (request.knowledge_base_id, 128)
    if request.session_id is not None:
        identifiers["session_id"] = (request.session_id, 128)
    for field, (value, max_length) in identifiers.items():
        if not value or len(value) > max_length:
            raise ValueError(f"{field} must contain between 1 and {max_length} characters")
    return plan


class MemoryAgent:
    def __init__(
        self,
        *,
        retriever: EvidenceRetriever,
        generator: AnswerGenerator,
        citation_validator: CitationValidator,
        runs: AnswerRunRepository | None = None,
        timeouts: PhaseTimeouts | None = None,
    ) -> None:
        self._retriever = retriever
        self._generator = generator
        self._citation_validator = citation_validator
        self._runs = runs or AnswerRunRepository()
        self._timeouts = timeouts or PhaseTimeouts()

    async def get_run(self, run_id: str) -> AnswerRunData:
        return await self._runs.get(run_id)

    async def _record_failure(
        self,
        *,
        run_id: str,
        mode: str,
        phase: RunPhase,
        started: float,
        error_code: str,
    ) -> None:
        # Failure persistence is best-effort and must not replace the original error/cancellation.
        try:
            await asyncio.shield(
                self._runs.fail(
                    run_id,
                    phase=phase,
                    duration_ms=_elapsed_ms(started),
                    error_code=error_code,
                )
            )
        except (Exception, asyncio.CancelledError):
            return
        safe_log(
            logger,
            logging.WARNING,
            "answer_phase",
            mode=mode,
            phase=phase,
            status="failed",
            error_code=error_code,
            duration_ms=_elapsed_ms(started),
        )

    async def _retrieve(
        self,
        request: AnswerRequest,
        plan: RetrievalPlan,
    ) -> tuple[list[RetrievedEvidence], int]:
        if not plan.uses_private_sources:
            return [], 0
        evidence = await self._retriever.retrieve(
            retrieval_request(request, plan, expansion_index=0)
        )
        expansion_count = 0
        if not evidence and plan.max_expansions == 1:
            expansion_count = 1
            evidence = await self._retriever.retrieve(
                retrieval_request(request, plan, expansion_index=1)
            )
        return evidence, expansion_count

    async def run(self, request: AnswerRequest) -> AnswerResponse:
        validate_started = perf_counter()
        try:
            async with asyncio.timeout(self._timeouts.validate):
                plan = _validate_request(request)
        except TimeoutError:
            # No run exists yet: validation precedes durable creation by design.
            raise RuntimeDependencyError("AGENT_VALIDATE_TIMEOUT") from None

        run_id = uuid4().hex
        await self._runs.create(
            run_id=run_id,
            request=request,
            validation_duration_ms=_elapsed_ms(validate_started),
        )
        safe_log(
            logger,
            logging.INFO,
            "answer_phase",
            mode=request.answer_mode,
            phase="validate",
            status="completed",
            duration_ms=_elapsed_ms(validate_started),
        )
        with observation_context(request_id=request.request_id, run_id=run_id):
            return await self._run_created(request=request, plan=plan, run_id=run_id)

    async def _run_created(
        self,
        *,
        request: AnswerRequest,
        plan: RetrievalPlan,
        run_id: str,
    ) -> AnswerResponse:
        phase: RunPhase = "retrieve"
        phase_started = perf_counter()
        try:
            await self._runs.begin_phase(run_id, previous="validate", phase=phase)
            try:
                async with asyncio.timeout(self._timeouts.retrieve):
                    evidence, expansion_count = await self._retrieve(request, plan)
            except TimeoutError:
                code = "AGENT_RETRIEVAL_TIMEOUT"
                await self._record_failure(
                    run_id=run_id,
                    mode=request.answer_mode,
                    phase=phase,
                    started=phase_started,
                    error_code=code,
                )
                raise AnswerRunExecutionError(run_id=run_id, error_code=code) from None
            except Exception as exc:
                code = _dependency_error_code(exc, phase)
                await self._record_failure(
                    run_id=run_id,
                    mode=request.answer_mode,
                    phase=phase,
                    started=phase_started,
                    error_code=code,
                )
                raise AnswerRunExecutionError(run_id=run_id, error_code=code) from None

            await self._runs.record_retrieval(
                run_id,
                duration_ms=_elapsed_ms(phase_started),
                source_ids=[item.source_id for item in evidence],
                expansion_count=expansion_count,
            )
            safe_log(
                logger,
                logging.INFO,
                "answer_phase",
                mode=request.answer_mode,
                phase="retrieve",
                status="completed",
                duration_ms=_elapsed_ms(phase_started),
            )

            phase = "generate"
            phase_started = perf_counter()
            await self._runs.begin_phase(run_id, previous="retrieve", phase=phase)
            try:
                async with asyncio.timeout(self._timeouts.generate):
                    generated = await self._generator.generate(
                        GenerationRequest(
                            request_id=request.request_id,
                            mode=request.answer_mode,
                            question=request.question,
                            evidence=evidence,
                            model=request.model,
                        )
                    )
            except TimeoutError:
                code = "AGENT_MODEL_TIMEOUT"
                await self._record_failure(
                    run_id=run_id,
                    mode=request.answer_mode,
                    phase=phase,
                    started=phase_started,
                    error_code=code,
                )
                raise AnswerRunExecutionError(run_id=run_id, error_code=code) from None
            except Exception as exc:
                code = _dependency_error_code(exc, phase)
                await self._record_failure(
                    run_id=run_id,
                    mode=request.answer_mode,
                    phase=phase,
                    started=phase_started,
                    error_code=code,
                )
                raise AnswerRunExecutionError(run_id=run_id, error_code=code) from None

            await self._runs.record_generation(
                run_id=run_id,
                duration_ms=_elapsed_ms(phase_started),
                answer=generated,
            )
            safe_log(
                logger,
                logging.INFO,
                "answer_phase",
                mode=request.answer_mode,
                phase="generate",
                status="completed",
                duration_ms=_elapsed_ms(phase_started),
            )

            phase = "citations"
            phase_started = perf_counter()
            await self._runs.begin_phase(run_id, previous="generate", phase=phase)
            try:
                async with asyncio.timeout(self._timeouts.citations):
                    citation_result = await asyncio.to_thread(
                        self._citation_validator.validate,
                        generated,
                        evidence,
                    )
            except TimeoutError:
                code = "AGENT_CITATION_TIMEOUT"
                await self._record_failure(
                    run_id=run_id,
                    mode=request.answer_mode,
                    phase=phase,
                    started=phase_started,
                    error_code=code,
                )
                raise AnswerRunExecutionError(run_id=run_id, error_code=code) from None
            except Exception as exc:
                code = _dependency_error_code(exc, phase)
                await self._record_failure(
                    run_id=run_id,
                    mode=request.answer_mode,
                    phase=phase,
                    started=phase_started,
                    error_code=code,
                )
                raise AnswerRunExecutionError(run_id=run_id, error_code=code) from None

            insufficient_evidence = (
                citation_result.insufficient_evidence
                or generated.insufficient_evidence
                or (plan.uses_private_sources and not evidence)
            )
            await self._runs.complete(
                run_id,
                citation_duration_ms=_elapsed_ms(phase_started),
                confidence=citation_result.confidence,
                uncertainty=citation_result.uncertainty,
                insufficient_evidence=insufficient_evidence,
            )
            citation_duration_ms = _elapsed_ms(phase_started)
            safe_log(
                logger,
                logging.INFO,
                "answer_phase",
                mode=request.answer_mode,
                phase="citations",
                status="completed",
                duration_ms=citation_duration_ms,
                count=int(insufficient_evidence),
            )

            memory_ids = list(
                dict.fromkeys(item.source_id for item in evidence if item.source_type == "memory")
            )
            document_ids = list(
                dict.fromkeys(item.source_id for item in evidence if item.source_type == "document")
            )
            return AnswerResponse(
                answer=generated.answer,
                mode=request.answer_mode,
                route=generated.route,
                citations=citation_result.citations,
                confidence=citation_result.confidence,
                uncertainty=citation_result.uncertainty,
                insufficient_evidence=insufficient_evidence,
                memory_ids=memory_ids,
                document_ids=document_ids,
                run_id=run_id,
            )
        except asyncio.CancelledError:
            await self._record_failure(
                run_id=run_id,
                mode=request.answer_mode,
                phase=phase,
                started=phase_started,
                error_code="AGENT_RUN_CANCELLED",
            )
            raise
