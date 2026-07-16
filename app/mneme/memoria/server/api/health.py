import asyncio
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.mneme.memoria.server.celery_app import celery_app
from app.mneme.memoria.server.config import settings
from app.mneme.memoria.server.database import get_db
from app.mneme.memoria.server.models.answer_run import AnswerRun
from app.mneme.memoria.server.models.document_projection import DocumentProjection
from app.mneme.memoria.server.models.inbox_event import InboxEvent
from app.mneme.memoria.server.models.memory_audit import MemoryActionAudit
from app.mneme.memoria.server.observability.metrics import OperationalMetrics, labels, render_metrics

router = APIRouter()


@router.get("/health")
async def liveness() -> dict[str, str]:
    """Process-only signal: it deliberately touches no external dependency."""
    return {"status": "ok"}


@router.get("/health/readiness")
async def readiness(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, object]:
    try:
        await db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="database unavailable",
        ) from exc
    service_model_configured = bool(
        settings.ANSWER_LLM_MODEL.strip() and settings.ANSWER_LLM_API_KEY.get_secret_value()
    )
    return {
        "status": "ready",
        "database": "ready",
        # Requests may supply an ephemeral model config, so this is diagnostic rather than fatal.
        "answer_model": "service_default" if service_model_configured else "request_required",
    }


def _worker_diagnostic() -> int:
    inspector = celery_app.control.inspect(timeout=2.0)
    queues_by_worker = inspector.active_queues() or {}
    return sum(
        1
        for queues in queues_by_worker.values()
        if any(queue.get("name") == settings.CELERY_QUEUE for queue in queues)
    )


@router.get("/health/worker")
async def worker_readiness(db: Annotated[AsyncSession, Depends(get_db)]) -> dict[str, object]:
    """Queue/worker dependency diagnostic, separate from API liveness/readiness."""
    try:
        pending = await db.scalar(
            select(func.count()).select_from(InboxEvent).where(InboxEvent.status == "pending")
        )
        worker_count = await asyncio.wait_for(asyncio.to_thread(_worker_diagnostic), timeout=3.0)
        if worker_count == 0:
            raise RuntimeError("no worker consumes the configured queue")
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="worker dependency unavailable",
        ) from exc
    return {
        "status": "ready",
        "database": "ready",
        "broker": "ready",
        "workers": worker_count,
        "inbox_backlog": pending or 0,
    }


async def _operational_metrics(db: AsyncSession) -> OperationalMetrics:
    now = datetime.now(UTC)
    inbox = (
        await db.execute(
            select(
                func.count().filter(InboxEvent.status == "pending"),
                func.count().filter(InboxEvent.status == "failed"),
                func.min(InboxEvent.received_at).filter(InboxEvent.status == "pending"),
            )
        )
    ).one()
    oldest_pending = inbox[2]
    oldest_staging = await db.scalar(
        select(func.min(DocumentProjection.created_at)).where(DocumentProjection.status == "staging")
    )
    failed_runs = await db.scalar(
        select(func.count()).select_from(AnswerRun).where(AnswerRun.status == "failed")
    )
    stale_runs = await db.scalar(
        select(func.count())
        .select_from(AnswerRun)
        .where(
            AnswerRun.status == "running",
            AnswerRun.started_at < now - timedelta(seconds=settings.ANSWER_RUN_STALE_SECONDS),
        )
    )
    model_stats = (
        await db.execute(
            text(
                "SELECT "
                "COALESCE(sum(GREATEST(jsonb_array_length(model_attempts) - 1, 0)), 0) AS retries, "
                "count(*) FILTER (WHERE fallback_used IS TRUE) AS fallbacks "
                "FROM answer_runs"
            )
        )
    ).one()
    actions = dict(
        await db.execute(select(MemoryActionAudit.action, func.count()).group_by(MemoryActionAudit.action))
    )
    run_rows = (
        await db.execute(
            text(
                "SELECT mode, status, COALESCE(error_code, 'none') AS error, count(*) AS value "
                "FROM answer_runs GROUP BY mode, status, COALESCE(error_code, 'none')"
            )
        )
    ).all()
    phase_rows = (
        await db.execute(
            text(
                "SELECT mode, phase.key AS phase, count(*) AS sample_count, "
                "COALESCE(sum(phase.value::numeric), 0) AS duration_sum "
                "FROM answer_runs CROSS JOIN LATERAL jsonb_each_text(phase_durations_ms) AS phase "
                "GROUP BY mode, phase.key"
            )
        )
    ).all()
    outcome_rows = (
        await db.execute(
            text(
                "SELECT mode, count(*) FILTER (WHERE insufficient_evidence IS TRUE) AS insufficient, "
                "COALESCE(sum(total_tokens), 0) AS tokens, COALESCE(sum(cost), 0) AS cost "
                "FROM answer_runs GROUP BY mode"
            )
        )
    ).all()
    return OperationalMetrics(
        inbox_backlog=inbox[0] or 0,
        dead_letters=inbox[1] or 0,
        oldest_inbox_age_seconds=max(0.0, (now - oldest_pending).total_seconds()) if oldest_pending else 0.0,
        projection_lag_seconds=max(0.0, (now - oldest_staging).total_seconds()) if oldest_staging else 0.0,
        failed_runs=failed_runs or 0,
        stale_runs=stale_runs or 0,
        model_retries=int(model_stats.retries or 0),
        model_fallbacks=int(model_stats.fallbacks or 0),
        governance_actions={str(action): count for action, count in actions.items()},
        answer_runs=tuple(
            (labels(mode=row.mode, status=row.status, error=row.error), row.value) for row in run_rows
        ),
        phase_duration_ms_count=tuple(
            (labels(mode=row.mode, phase=row.phase), row.sample_count) for row in phase_rows
        ),
        phase_duration_ms_sum=tuple(
            (labels(mode=row.mode, phase=row.phase), float(row.duration_sum)) for row in phase_rows
        ),
        insufficient_evidence=tuple(
            (labels(mode=row.mode), row.insufficient) for row in outcome_rows
        ),
        answer_tokens=tuple((labels(mode=row.mode), row.tokens) for row in outcome_rows),
        answer_cost=tuple((labels(mode=row.mode), float(row.cost)) for row in outcome_rows),
    )


@router.get("/metrics", include_in_schema=False)
async def metrics(db: Annotated[AsyncSession, Depends(get_db)]) -> Response:
    snapshot = await _operational_metrics(db)
    return Response(render_metrics(snapshot), media_type="text/plain; version=0.0.4")
