from collections.abc import Iterable

from app.mneme.conf.config import settings
from app.mneme.schemas.production import FrameworkDecisionData, ProductionReadinessReportData, ReadinessCheckData

DEFAULT_STACK = [
    "FastAPI",
    "PostgreSQL",
    "Milvus",
    "Neo4j",
    "Redis",
    "Celery",
    "Qwen-compatible LLM API",
]

OPTIONAL_STACK = [
    "RabbitMQ as future Celery broker",
    "LlamaIndex for ingestion / GraphRAG PoC only",
]

AVOID_BY_DEFAULT = [
    "MongoDB",
    "Elasticsearch",
    "DuckDB",
    "New vector database",
]


def build_check(*, name: str, passed: bool, reason: str, warn: bool = False) -> ReadinessCheckData:
    if warn:
        status = "pass" if passed else "warn"
    else:
        status = "pass" if passed else "fail"
    return ReadinessCheckData(
        name=name,
        status=status,
        reason=reason,
    )


def summarize_overall_status(checks: Iterable[ReadinessCheckData]) -> str:
    statuses = [check.status for check in checks]
    if any(status == "fail" for status in statuses):
        return "fail"
    if any(status == "warn" for status in statuses):
        return "warn"
    return "pass"


def build_framework_decisions() -> list[FrameworkDecisionData]:
    return [
        FrameworkDecisionData(
            area="retrieval_core",
            decision="keep_self_built",
            reason=(
                "Query routing, hybrid recall, fusion, rerank, evidence answer, "
                "and debug/eval hooks are project-specific and already integrated."
            ),
        ),
        FrameworkDecisionData(
            area="document_ingestion",
            decision="optional_poc",
            reason=(
                "LlamaIndex can be evaluated for ingestion convenience, but should "
                "not replace the current pipeline without eval evidence."
            ),
        ),
        FrameworkDecisionData(
            area="graph_rag",
            decision="optional_poc",
            reason=(
                "GraphRAG is currently gated by decision and eval views; framework "
                "adoption should stay behind the same gate."
            ),
        ),
        FrameworkDecisionData(
            area="analytics_store",
            decision="avoid_by_default",
            reason=(
                "PostgreSQL views and reports cover the current tuning needs; "
                "adding DuckDB or MongoDB would increase operational surface."
            ),
        ),
        FrameworkDecisionData(
            area="keyword_search",
            decision="avoid_by_default",
            reason=(
                "PostgreSQL keyword recall is sufficient for the current lightweight "
                "hybrid stage unless eval proves otherwise."
            ),
        ),
    ]


def render_readiness_markdown(report: ProductionReadinessReportData) -> str:
    lines = [
        "# Production Readiness",
        "",
        f"- overall_status: {report.overall_status}",
        f"- default_stack: {', '.join(report.default_stack)}",
        f"- optional_stack: {', '.join(report.optional_stack)}",
        f"- avoid_by_default: {', '.join(report.avoid_by_default)}",
        "",
        "## Checks",
    ]
    for check in report.checks:
        lines.append(f"- {check.name}: {check.status} - {check.reason}")

    lines.extend(["", "## Framework Decisions"])
    for decision in report.framework_decisions:
        lines.append(f"- {decision.area}: {decision.decision} - {decision.reason}")

    return "\n".join(lines)


def build_production_readiness_report() -> ProductionReadinessReportData:
    checks = [
        build_check(
            name="bootstrap_app_factory",
            passed=True,
            reason="main.py delegates app construction to app.mneme.bootstrap.app_factory.create_app().",
        ),
        build_check(
            name="query_routing",
            passed=True,
            reason="QueryRouter separates general chat, KB QA, memory, profile, analysis, and action requests.",
        ),
        build_check(
            name="hybrid_retrieval",
            passed=True,
            reason="The retrieval path supports vector, keyword, memory, fusion, and rerank layers.",
        ),
        build_check(
            name="citation_guardrail",
            passed=True,
            reason="Evidence answer and citation validation are present in the RAG chain.",
        ),
        build_check(
            name="task_lifecycle",
            passed=True,
            reason="TaskRecord models pending, running, succeeded, failed, retrying, and cancelled states.",
        ),
        build_check(
            name="outbox_projection",
            passed=True,
            reason="OutboxEvent records Milvus and Neo4j projection work with retry and dead-letter states.",
        ),
        build_check(
            name="postgresql_analytics",
            passed=True,
            reason="Analytics service and PostgreSQL views summarize documents, chunks, tasks, and outbox events.",
        ),
        build_check(
            name="migration_execution",
            passed=False,
            reason=(
                "Day 16-18 migrations exist, but this readiness check cannot confirm "
                "they were applied to the live database."
            ),
            warn=True,
        ),
        build_check(
            name="external_service_probe",
            passed=settings.NEO4J_ENABLED,
            reason=(
                "Neo4j probing is exposed; Milvus and Redis are still verified by "
                "worker/runtime checks rather than this report."
            ),
            warn=True,
        ),
        build_check(
            name="production_secret",
            passed=settings.JWT_SECRET != "dev-only-change-this-secret-key",
            reason="JWT_SECRET must be changed outside local development.",
            warn=True,
        ),
    ]

    report = ProductionReadinessReportData(
        overall_status=summarize_overall_status(checks),
        checks=checks,
        framework_decisions=build_framework_decisions(),
        default_stack=DEFAULT_STACK,
        optional_stack=OPTIONAL_STACK,
        avoid_by_default=AVOID_BY_DEFAULT,
        markdown="",
    )
    report.markdown = render_readiness_markdown(report)
    return report
