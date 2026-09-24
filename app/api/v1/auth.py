"""提供 API 的认证和授权接口.

本模块包含用户注册、登录、会话管理和令牌校验接口.
"""

import uuid
from typing import List

from fastapi import (
    APIRouter,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from app.core.config import settings
from app.core.limiter import limiter
from app.core.logging import (
    bind_context,
    logger,
)
from app.models.session import Session
from app.models.user import User
from app.schemas.auth import (
    SessionResponse,
    TokenResponse,
    UserCreate,
    UserResponse,
)
from app.services.database import database_service
from app.utils.auth import (
    create_access_token,
    verify_token,
)
from app.utils.sanitization import (
    sanitize_email,
    sanitize_string,
    validate_password_strength,
)

router = APIRouter()  # 注册一个 API 路由器
security = (
    HTTPBearer()
)  # 定义一个基于 Bearer Token（通常是 JWT）的安全认证依赖机制，它会自动检查请求头中的 Authorization 字段
db_service = (
    database_service  # 复用共享实例；DatabaseService.__init__ 会创建自己的引擎，重复实例化会产生两个独立的连接池.
)


# 复用方法，一般用于依赖注入
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User:
    """从令牌中获取当前用户.

    参数：
        credentials: 包含 JWT 令牌的 HTTP 认证凭据.

    返回：
        从令牌中解析并查询到的用户.

    异常：
        HTTPException: 令牌无效或缺失时抛出异常.
    """
    try:
        # 清理令牌
        token = sanitize_string(credentials.credentials)

        user_id = verify_token(token)
        if user_id is None:
            logger.error("invalid_token", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 检查用户是否存在于数据库中
        user_id_int = int(user_id)
        user = await db_service.get_user(user_id_int)
        if user is None:
            logger.error("user_not_found", user_id=user_id_int)
            raise HTTPException(
                status_code=404,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 将 user_id 绑定到日志上下文，供本次请求后续日志使用
        bind_context(user_id=user_id_int)

        return user
    except ValueError as ve:
        logger.exception("token_validation_failed", error=str(ve))
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


# 获取当前会话，一般用于依赖注入
async def get_current_session(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> Session:
    """从令牌中获取当前会话.

    参数：
        credentials: 包含 JWT 令牌的 HTTP 认证凭据.

    返回：
        从令牌中解析并查询到的会话.

    异常：
        HTTPException: 令牌无效或缺失时抛出异常.
    """
    try:
        # 清理令牌
        token = sanitize_string(credentials.credentials)

        session_id = verify_token(token)
        if session_id is None:
            logger.error("session_id_not_found", token_part=token[:10] + "...")
            raise HTTPException(
                status_code=401,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 使用 session_id 前先进行清理
        session_id = sanitize_string(session_id)

        # 检查会话是否存在于数据库中
        session = await db_service.get_session(session_id)
        if session is None:
            logger.error("session_not_found", session_id=session_id)
            raise HTTPException(
                status_code=404,
                detail="Session not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 将 user_id 绑定到日志上下文，供本次请求后续日志使用
        bind_context(user_id=session.user_id)

        return session
    except ValueError as ve:
        logger.exception("token_validation_failed", error=str(ve))
        raise HTTPException(
            status_code=422,
            detail="Invalid token format",
            headers={"WWW-Authenticate": "Bearer"},
        )


@router.post("/register", response_model=UserResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["register"][0])
async def register_user(request: Request, user_data: UserCreate):
    """注册新用户.

    参数：
        request: 用于限流的 FastAPI 请求对象.
        user_data: 用户注册信息.

    返回：
        新创建的用户信息.
    """
    try:
        # 清理邮箱地址
        sanitized_email = sanitize_email(user_data.email)

        # 提取并校验密码
        password = user_data.password.get_secret_value()
        validate_password_strength(password)

        # 检查用户是否已存在
        if await db_service.get_user_by_email(sanitized_email):
            raise HTTPException(status_code=400, detail="Email already registered")

        # 清理可选的用户名
        sanitized_username = sanitize_string(user_data.username) if user_data.username else None

        # 创建用户
        user = await db_service.create_user(
            email=sanitized_email,
            password=User.hash_password(password),
            username=sanitized_username,
        )

        # 创建访问令牌
        token = create_access_token(str(user.id))

        return UserResponse(id=user.id, email=user.email, username=user.username, token=token)
    except ValueError as ve:
        logger.exception("user_registration_validation_failed", error=str(ve))
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/login", response_model=TokenResponse)
@limiter.limit(settings.RATE_LIMIT_ENDPOINTS["login"][0])
async def login(
    request: Request, email: str = Form(...), password: str = Form(...), grant_type: str = Form(default="password")
):
    """用户登录.

    参数：
        request: 用于限流的 FastAPI 请求对象.
        email: 用户邮箱.
        password: 用户密码.
        grant_type: 必须为 ``password``.

    返回：
        访问令牌信息.

    异常：
        HTTPException: 认证信息无效时抛出异常.
    """
    try:
        # 清理输入参数
        email = sanitize_string(email)
        grant_type = sanitize_string(grant_type)

        # 校验授权类型
        if grant_type != "password":
            raise HTTPException(
                status_code=400,
                detail="Unsupported grant type. Must be 'password'",
            )

        user = await db_service.get_user_by_email(email)
        if not user or not user.verify_password(password):
            raise HTTPException(
                status_code=401,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(str(user.id))
        return TokenResponse(access_token=token.access_token, token_type="bearer", expires_at=token.expires_at)
    except ValueError as ve:
        logger.exception("login_validation_failed", error=str(ve))
        raise HTTPException(status_code=422, detail=str(ve))


@router.post("/session", response_model=SessionResponse)
async def create_session(user: User = Depends(get_current_user)):
    """为已认证用户创建新的聊天会话.

    参数：
        user: 已认证的用户.

    返回：
        包含会话 ID、名称和访问令牌的响应.
    """
    try:
        # 生成唯一的会话 ID
        session_id = str(uuid.uuid4())

        # 在数据库中创建会话，同时复制用户名用于个性化 LLM 交互
        session = await db_service.create_session(session_id, user.id, username=user.username)

        # 为会话创建访问令牌
        token = create_access_token(session_id)

        logger.info(
            "session_created",
            session_id=session_id,
            user_id=user.id,
            name=session.name,
            expires_at=token.expires_at.isoformat(),
        )

        return SessionResponse(session_id=session_id, name=session.name, token=token)
    except ValueError as ve:
        logger.exception("session_creation_validation_failed", error=str(ve), user_id=user.id)
        raise HTTPException(status_code=422, detail=str(ve))


@router.patch("/session/{session_id}/name", response_model=SessionResponse)
async def update_session_name(
    session_id: str, name: str = Form(...), current_session: Session = Depends(get_current_session)
):
    """更新会话名称.

    参数：
        session_id: 要更新的会话 ID.
        name: 会话的新名称.
        current_session: 通过认证获取的当前会话.

    返回：
        更新后的会话信息.
    """
    try:
        # 清理输入参数
        sanitized_session_id = sanitize_string(session_id)
        sanitized_name = sanitize_string(name)
        sanitized_current_session = sanitize_string(current_session.id)

        # 校验会话 ID 是否与当前认证会话一致
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="Cannot modify other sessions")

        # 更新会话名称
        session = await db_service.update_session_name(sanitized_session_id, sanitized_name)

        # 创建新的令牌；虽然不是必须的，但可以保持返回结构一致
        token = create_access_token(sanitized_session_id)

        return SessionResponse(session_id=sanitized_session_id, name=session.name, token=token)
    except ValueError as ve:
        logger.exception("session_update_validation_failed", error=str(ve), session_id=session_id)
        raise HTTPException(status_code=422, detail=str(ve))


@router.delete("/session/{session_id}")
async def delete_session(session_id: str, current_session: Session = Depends(get_current_session)):
    """删除已认证用户的会话.

    参数：
        session_id: 要删除的会话 ID.
        current_session: 通过认证获取的当前会话.

    返回：
        无返回值.
    """
    try:
        # 清理输入参数
        sanitized_session_id = sanitize_string(session_id)
        sanitized_current_session = sanitize_string(current_session.id)

        # 校验会话 ID 是否与当前认证会话一致
        if sanitized_session_id != sanitized_current_session:
            raise HTTPException(status_code=403, detail="Cannot delete other sessions")

        # 删除会话
        await db_service.delete_session(sanitized_session_id)

        logger.info("session_deleted", session_id=session_id, user_id=current_session.user_id)
    except ValueError as ve:
        logger.exception("session_deletion_validation_failed", error=str(ve), session_id=session_id)
        raise HTTPException(status_code=422, detail=str(ve))


@router.get("/sessions", response_model=List[SessionResponse])
async def get_user_sessions(user: User = Depends(get_current_user)):
    """获取已认证用户的全部会话.

    参数：
        user: 已认证的用户.

    返回：
        会话信息列表.
    """
    try:
        sessions = await db_service.get_user_sessions(user.id)
        return [
            SessionResponse(
                session_id=sanitize_string(session.id),
                name=sanitize_string(session.name),
                token=create_access_token(session.id),
            )
            for session in sessions
        ]
    except ValueError as ve:
        logger.exception("get_sessions_validation_failed", user_id=user.id, error=str(ve))
        raise HTTPException(status_code=422, detail=str(ve))
