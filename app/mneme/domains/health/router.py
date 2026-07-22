from fastapi import APIRouter
from fastapi.responses import Response

from app.mneme.domains.graph.admin import get_neo4j_health_status
from app.mneme.domains.health.readiness import build_production_readiness_report
from app.mneme.observability.http import render_http_metrics
from app.mneme.schemas.graph_admin import Neo4jHealthData
from app.mneme.schemas.production import ProductionReadinessReportData
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    return success_response(
        data={"service": "mneme", "status": "running"},
        message="service is healthy",
    )


@router.get("/metrics", include_in_schema=False)
def metrics():
    from app.mneme.bootstrap.app_factory import mneme_http_metrics

    return Response(
        render_http_metrics(mneme_http_metrics, prefix="mneme"),
        media_type="text/plain; version=0.0.4",
    )


@router.get("/neo4j")
async def neo4j_health_check():
    data = await get_neo4j_health_status()
    return success_response(
        data=Neo4jHealthData(**data),
        message="neo4j health checked",
    )


@router.get("/readiness")
async def production_readiness_check():
    report = build_production_readiness_report()
    return success_response(
        data=ProductionReadinessReportData.model_validate(report),
        message="production readiness checked",
    )
