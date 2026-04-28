from fastapi import APIRouter

from schemas.graph_admin import Neo4jHealthData
from services.graph_admin_service import get_neo4j_health_status
from utils.response import success_response

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
def health_check():
    # 健康检查接口一般不做复杂逻辑，它的主要任务是告诉你：
    # 服务是否启动了，路由是否注册成功了。
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
