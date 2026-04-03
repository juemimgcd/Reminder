from fastapi import APIRouter

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