"""用于跟踪指标和处理其他横切关注点的自定义中间件."""

import json
import time
import tracemalloc
from typing import (
    TYPE_CHECKING,
    Callable,
    override,
)

from asgi_correlation_id import correlation_id
from fastapi import Request
from jose import (
    JWTError,
    jwt,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from app.core.config import settings
from app.core.logging import (
    bind_context,
    clear_context,
    logger,
)
from app.core.metrics import (
    http_request_duration_seconds,
    http_requests_total,
)

if TYPE_CHECKING:
    from pyinstrument import Profiler  # pyright: ignore[reportMissingImports]
    from pyinstrument.renderers import JSONRenderer  # pyright: ignore[reportMissingImports]

    PYINSTRUMENT_AVAILABLE = True
else:
    try:
        from pyinstrument import Profiler
        from pyinstrument.renderers import JSONRenderer

        PYINSTRUMENT_AVAILABLE = True
    except ImportError:
        Profiler = None
        JSONRenderer = None
        PYINSTRUMENT_AVAILABLE = False


class MetricsMiddleware(BaseHTTPMiddleware):
    """用于跟踪 HTTP 请求指标的中间件."""

    @override
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """跟踪每个请求的指标.

        参数：
            request: 当前进入的请求.
            call_next: 下一个中间件或路由处理器.

        返回：
            Response: 应用返回的响应.
        """
        start_time = time.time()
        status_code = 500

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception:
            raise
        finally:
            duration = time.time() - start_time

            # 记录指标
            http_requests_total.labels(method=request.method, endpoint=request.url.path, status=status_code).inc()

            http_request_duration_seconds.labels(method=request.method, endpoint=request.url.path).observe(duration)

        return response


class LoggingContextMiddleware(BaseHTTPMiddleware):
    """用于将 user_id 和 session_id 添加到日志上下文的中间件."""

    @override
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """从已认证请求中提取 user_id 和 session_id，并添加到日志上下文.

        参数：
            request: 当前进入的请求.
            call_next: 下一个中间件或路由处理器.

        返回：
            Response: 应用返回的响应.
        """
        try:
            # 清理上一个请求可能遗留的上下文
            clear_context()

            # 从 Authorization 请求头中提取令牌
            auth_header = request.headers.get("authorization")
            if auth_header and auth_header.startswith("Bearer "):
                token = auth_header.split(" ")[1]

                try:
                    # 解码令牌获取 session_id；session_id 存储在 "sub" 声明中
                    payload = jwt.decode(token, settings.JWT_SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
                    session_id = payload.get("sub")

                    if session_id:
                        # 将 session_id 绑定到日志上下文
                        bind_context(session_id=session_id)

                        # 尝试在认证完成后从请求状态中获取 user_id.
                        # 如果接口使用认证依赖注入，该值会被设置；请求处理完成后再进行检查.

                except JWTError:
                    # 令牌无效时不直接中断请求，交由认证依赖处理
                    pass

            # 处理请求
            response = await call_next(request)

            # 请求处理完成后，检查请求状态中是否已写入用户信息
            if hasattr(request.state, "user_id"):
                bind_context(user_id=request.state.user_id)

            return response

        finally:
            # 请求完成后始终清理上下文，避免泄漏到其他请求
            clear_context()


class ProfilingMiddleware(BaseHTTPMiddleware):
    """使用 pyinstrument 对每个请求自动进行性能分析的中间件.

    仅在 DEBUG=true 时启用.该中间件会分析每个请求，当请求耗时超过
    PROFILING_THRESHOLD_SECONDS 时，将性能分析结果保存到 PROFILING_DIR.
    文件名为 {request_id}.html，以便与日志关联；/tmp 目录由操作系统自动清理.
    """

    @override
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """分析每个请求，耗时超过阈值时保存详细 JSON 报告."""
        if not PYINSTRUMENT_AVAILABLE:
            return await call_next(request)

        # 启动三类性能分析器
        tracemalloc.start()
        cpu_start = time.process_time()

        profiler = Profiler(async_mode="enabled")
        with profiler:
            response = await call_next(request)

        # 请求完成后立即采集指标
        cpu_ms = round((time.process_time() - cpu_start) * 1000, 2)
        mem_current_kb, mem_peak_kb = (v // 1024 for v in tracemalloc.get_traced_memory())
        snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()

        wall_ms = round((profiler.last_session.duration if profiler.last_session else 0.0) * 1000, 2)

        if wall_ms / 1000 >= settings.PROFILING_THRESHOLD_SECONDS:
            raw_id = correlation_id.get() or "unknown"
            if len(raw_id) == 32 and "-" not in raw_id:
                raw_id = f"{raw_id[:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:]}"

            settings.PROFILING_DIR.mkdir(parents=True, exist_ok=True)
            filepath = settings.PROFILING_DIR / f"{raw_id}.json"

            # 获取内存占用最多的前 20 个位置，排除性能分析器和标准库产生的噪声
            _excluded = ("tracemalloc", "pyinstrument", "<frozen", "logging/__init__")
            top_allocs = [
                {
                    "file": str(stat.traceback[0].filename).replace(str(__file__).rsplit("/", 3)[0] + "/", ""),
                    "line": stat.traceback[0].lineno,
                    "size_kb": round(stat.size / 1024, 2),
                    "count": stat.count,
                }
                for stat in snapshot.statistics("lineno")
                if not any(ex in str(stat.traceback[0].filename) for ex in _excluded)
            ]

            call_tree = json.loads(profiler.output(renderer=JSONRenderer()))
            report = {
                "request_id": raw_id,
                "endpoint": f"{request.method} {request.url.path}",
                "wall_time_ms": wall_ms,
                "cpu_time_ms": cpu_ms,
                "io_wait_ms": round(wall_ms - cpu_ms, 2),
                "memory_peak_kb": mem_peak_kb,
                "memory_allocated_kb": mem_current_kb,
                "top_memory_allocators": top_allocs,
                "call_tree": call_tree,
            }
            filepath.write_text(json.dumps(report, indent=2))
            logger.debug(
                "slow_request_profile_saved",
                path=request.url.path,
                method=request.method,
                wall_time_ms=wall_ms,
                cpu_time_ms=cpu_ms,
                memory_peak_kb=mem_peak_kb,
                io_wait_ms=round(wall_ms - cpu_ms, 2),
                profile_file=str(filepath),
            )

        return response
