"""API v1 路由配置.

本模块创建主 API 路由，并引入认证、聊天机器人等不同功能的子路由.
"""

from fastapi import APIRouter

from app.api.v1.auth import router as auth_router
from app.api.v1.chatbot import router as chatbot_router
from app.core.logging import logger

api_router = APIRouter()

# 注册子路由
# 疑问：api_router.include_router(auth_router）注册的明明是auth_router，auth.py 声明的却是router = APIRouter()，为什么能跳转
# 答案：因为决定它们是同一个对象的不是定义时的名称，而是导入时使用的 import ... as ... 重命名机制.确实有 from app.api.v1.auth import router as auth_router

api_router.include_router(auth_router, prefix="/auth", tags=["Auth"])
api_router.include_router(chatbot_router, prefix="/chatbot", tags=["Chatbot"])


@api_router.get("/health")
async def health_check():
    """健康检查接口.

    返回：
        dict: 健康状态信息.
    """
    logger.info("health_check_called")
    return {"status": "healthy", "version": "1.0.0"}
