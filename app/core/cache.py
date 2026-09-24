"""提供可选 Redis/Valkey 后端的缓存服务.

配置 VALKEY_HOST 后，使用 Redis 客户端连接 Valkey 实现分布式缓存；否则回退到简单的内存 TTL 缓存.
"""

import hashlib
import time
from typing import (
    TYPE_CHECKING,
    Awaitable,
    Optional,
    cast,
)

from app.core.config import settings
from app.core.logging import logger

# 尝试导入 redis；该依赖是可选的
if TYPE_CHECKING:
    from redis.asyncio import Redis  # pyright: ignore[reportMissingImports]

    REDIS_AVAILABLE = True
else:
    try:
        from redis.asyncio import Redis

        REDIS_AVAILABLE = True
    except ImportError:
        logger.debug("redis_not_available")
        Redis = None
        REDIS_AVAILABLE = False


class InMemoryCacheService:
    """Valkey 不可用时使用的简单内存 TTL 缓存."""

    def __init__(self, default_ttl: int = 60):
        """初始化内存缓存.

        参数：
            default_ttl: 缓存条目的默认存活时间，单位为秒.
        """
        self._cache: dict[str, tuple[float, str]] = {}
        self._default_ttl = default_ttl

    async def initialize(self) -> None:
        """内存缓存无需执行初始化操作."""
        logger.info("cache_initialized", backend="in_memory", ttl=self._default_ttl)

    async def get(self, key: str) -> Optional[str]:
        """从缓存中获取值.

        参数：
            key: 缓存键.

        返回：
            缓存值；不存在或已过期时返回 None.
        """
        entry = self._cache.get(key)
        if entry is None:
            return None
        expires_at, value = entry
        if time.monotonic() > expires_at:
            del self._cache[key]
            return None
        return value

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """将值按 TTL 写入缓存.

        参数：
            key: 缓存键.
            value: 要缓存的值.
            ttl: 存活时间，单位为秒；未指定时使用默认值.
        """
        expires_at = time.monotonic() + (ttl or self._default_ttl)
        self._cache[key] = (expires_at, value)

    async def delete(self, key: str) -> None:
        """删除缓存中的值.

        参数：
            key: 缓存键.
        """
        self._cache.pop(key, None)

    async def close(self) -> None:
        """清空内存缓存."""
        self._cache.clear()


class ValkeyCacheService:
    """用于分布式缓存的 Redis/Valkey 缓存后端."""

    def __init__(self, default_ttl: int = 60):
        """使用 Redis 客户端初始化缓存服务.

        参数：
            default_ttl: 缓存条目的默认存活时间，单位为秒.
        """
        self._client: Optional[Redis] = None
        self._default_ttl = default_ttl

    async def initialize(self) -> None:
        """连接 Redis/Valkey 服务."""
        client = Redis(
            host=settings.VALKEY_HOST,
            port=settings.VALKEY_PORT,
            db=settings.VALKEY_DB,
            password=settings.VALKEY_PASSWORD or None,
            max_connections=settings.VALKEY_MAX_CONNECTIONS,
            decode_responses=True,
        )
        await cast(Awaitable[bool], client.ping())
        self._client = client
        logger.info(
            "cache_initialized",
            backend="redis",
            host=settings.VALKEY_HOST,
            port=settings.VALKEY_PORT,
            ttl=self._default_ttl,
        )

    async def get(self, key: str) -> Optional[str]:
        """从 Valkey 获取值.

        参数：
            key: 缓存键.

        返回：
            缓存值；不存在时返回 None.
        """
        if not self._client:
            return None
        try:
            return await self._client.get(key)
        except Exception as e:
            logger.warning("cache_get_failed", key=key, error=str(e))
            return None

    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> None:
        """将值按 TTL 写入 Valkey.

        参数：
            key: 缓存键.
            value: 要缓存的值.
            ttl: 存活时间，单位为秒；未指定时使用默认值.
        """
        if not self._client:
            return
        try:
            await self._client.set(key, value, ex=(ttl or self._default_ttl))
        except Exception as e:
            logger.warning("cache_set_failed", key=key, error=str(e))

    async def delete(self, key: str) -> None:
        """删除 Valkey 中的值.

        参数：
            key: 缓存键.
        """
        if not self._client:
            return
        try:
            await self._client.delete(key)
        except Exception as e:
            logger.warning("cache_delete_failed", key=key, error=str(e))

    async def close(self) -> None:
        """关闭 Valkey 连接."""
        if self._client:
            await self._client.aclose()
            logger.info("cache_connection_closed")


def _create_cache_service() -> InMemoryCacheService | ValkeyCacheService:
    """根据配置创建合适的缓存服务.

    返回：
        缓存服务实例；配置 Redis 时返回 Redis 服务，否则返回内存服务.
    """
    ttl = settings.CACHE_TTL_SECONDS

    if settings.VALKEY_HOST and REDIS_AVAILABLE:
        return ValkeyCacheService(default_ttl=ttl)

    if settings.VALKEY_HOST and not REDIS_AVAILABLE:
        logger.warning(
            "redis_client_not_installed",
            hint="install with: uv add redis --optional cache",
        )

    return InMemoryCacheService(default_ttl=ttl)


def cache_key(prefix: str, *parts: str) -> str:
    """使用前缀和哈希后的组成部分构建缓存键.

    参数：
        prefix: 缓存键前缀，例如 ``memory``.
        *parts: 要加入缓存键的其他组成部分.

    返回：
        可确定的缓存键字符串.
    """
    raw = ":".join(parts)
    hashed = hashlib.sha256(raw.encode()).hexdigest()[:16]
    return f"{prefix}:{hashed}"


# 全局缓存服务单例；在 lifespan 中延迟初始化
cache_service = _create_cache_service()
