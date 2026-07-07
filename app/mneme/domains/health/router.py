from fastapi import APIRouter

from app.mneme.schemas.graph_admin import Neo4jHealthData
from app.mneme.schemas.production import ProductionReadinessReportData
from app.mneme.domains.graph.admin import get_neo4j_health_status
from app.mneme.domains.health.readiness import build_production_readiness_report
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    return success_response(
        data={"service": "agentic-rag", "status": "running"},
        message="service is healthy",
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
