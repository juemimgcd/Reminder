from fastapi import APIRouter

from app.mneme.schemas.graph_admin import Neo4jHealthData
from app.mneme.schemas.production import ProductionReadinessReportData
from app.mneme.services.graph_admin_service import get_neo4j_health_status
from app.mneme.services.production_readiness_service import build_production_readiness_report
from app.mneme.utils.response import success_response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    # 鍋ュ悍妫€鏌ユ帴鍙ｄ竴鑸笉鍋氬鏉傞€昏緫锛屽畠鐨勪富瑕佷换鍔℃槸鍛婅瘔浣狅細
    # 鏈嶅姟鏄惁鍚姩浜嗭紝璺敱鏄惁娉ㄥ唽鎴愬姛浜嗐€?
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
