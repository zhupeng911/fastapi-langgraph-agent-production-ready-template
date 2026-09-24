"""应用限流配置.

本模块使用 slowapi 配置限流，默认限制由应用配置提供，并根据客户端远程 IP 地址进行限流.

配置 Valkey 后将使用 Valkey 作为分布式存储后端，确保多应用实例之间的限流状态一致.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

from app.core.cache import REDIS_AVAILABLE
from app.core.config import settings
from app.core.logging import logger

# 如果配置了 Valkey，则构建存储 URI.redis 是可选依赖（cache 扩展），缺少时回退到内存存储，
# 避免在模块导入阶段因限流配置抛出 ConfigurationError.
_storage_uri = None
if settings.VALKEY_HOST and REDIS_AVAILABLE:
    _password_part = f":{settings.VALKEY_PASSWORD}@" if settings.VALKEY_PASSWORD else ""
    _storage_uri = f"redis://{_password_part}{settings.VALKEY_HOST}:{settings.VALKEY_PORT}/{settings.VALKEY_DB}"
    logger.info("rate_limiter_using_valkey", host=settings.VALKEY_HOST, port=settings.VALKEY_PORT)
elif settings.VALKEY_HOST:
    logger.warning(
        "rate_limiter_valkey_configured_but_redis_missing",
        hint="install with: uv add redis --optional cache",
    )

# 初始化限流器；未配置 Valkey 时使用内存存储
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=settings.RATE_LIMIT_DEFAULT,  # pyright: ignore[reportArgumentType]
    storage_uri=_storage_uri,
)
