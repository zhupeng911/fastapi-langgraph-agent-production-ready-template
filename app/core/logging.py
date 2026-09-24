"""应用日志配置和初始化.

本模块使用 structlog 提供结构化日志配置，并根据不同环境配置格式化器和处理器，
同时支持适合开发环境的控制台日志和生产环境的 JSON 格式日志.
"""

import json
import logging
import sys
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import (
    Any,
    Dict,
    List,
    Optional,
    override,
)

import structlog
from asgi_correlation_id import correlation_id

from app.core.config import (
    Environment,
    settings,
)

# 确保日志目录存在
settings.LOG_DIR.mkdir(parents=True, exist_ok=True)

# 用于保存请求级数据的上下文变量
_request_context: ContextVar[Optional[Dict[str, Any]]] = ContextVar("request_context", default=None)


def bind_context(**kwargs: Any) -> None:
    """将上下文变量绑定到当前请求.

    参数：
        **kwargs: 要绑定到日志上下文的键值对.
    """
    current = _request_context.get() or {}
    _request_context.set({**current, **kwargs})


def clear_context() -> None:
    """清理当前请求的全部上下文变量."""
    _request_context.set(None)


def get_context() -> Dict[str, Any]:
    """获取当前日志上下文.

    返回：
        Dict[str, Any]: 当前上下文字典.
    """
    return _request_context.get() or {}


def add_context_to_event_dict(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """将上下文变量添加到事件字典.

    该处理器会将已绑定的上下文变量添加到每条日志事件中.

    参数：
        logger: 日志实例.
        method_name: 日志方法名称.
        event_dict: 要修改的事件字典.

    返回：
        Dict[str, Any]: 添加上下文变量后的事件字典.
    """
    context = get_context()
    if context:
        event_dict.update(context)
    return event_dict


def add_request_id_to_event_dict(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """将当前 request_id（来自 asgi-correlation-id）添加到每条日志事件.

    参数：
        logger: 日志实例.
        method_name: 日志方法名称.
        event_dict: 要修改的事件字典.

    返回：
        Dict[str, Any]: 添加 request_id 后的事件字典.
    """
    request_id = correlation_id.get()
    if request_id:
        event_dict["request_id"] = request_id
    return event_dict


def get_log_file_path() -> Path:
    """根据日期和环境获取当前日志文件路径.

    返回：
        Path: 日志文件路径.
    """
    env_prefix = settings.ENVIRONMENT.value
    return settings.LOG_DIR / f"{env_prefix}-{datetime.now().strftime('%Y-%m-%d')}.jsonl"


class JsonlFileHandler(logging.Handler):
    """用于将 JSONL 日志写入每日文件的自定义处理器."""

    def __init__(self, file_path: Path):
        """初始化 JSONL 文件处理器.

        参数：
            file_path: 写入日志条目的文件路径.
        """
        super().__init__()
        self.file_path = file_path

    @override
    def emit(self, record: logging.LogRecord) -> None:
        """将日志记录写入 JSONL 文件."""
        try:
            log_entry = {
                "timestamp": datetime.fromtimestamp(record.created).isoformat(),
                "level": record.levelname,
                "message": record.getMessage(),
                "module": record.module,
                "function": record.funcName,
                "filename": record.pathname,
                "line": record.lineno,
                "environment": settings.ENVIRONMENT.value,
            }
            extra = getattr(record, "extra", None)
            if isinstance(extra, dict):
                log_entry.update(extra)

            with open(self.file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception:
            self.handleError(record)

    @override
    def close(self) -> None:
        """关闭处理器."""
        super().close()


def get_structlog_processors(include_file_info: bool = True) -> List[Any]:
    """根据配置获取 structlog 处理器.

    参数：
        include_file_info: 是否在日志中包含文件信息.

    返回：
        List[Any]: structlog 处理器列表.
    """
    # 配置两种输出格式共用的处理器
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        # 将上下文变量（user_id、session_id 等）添加到所有日志事件
        add_context_to_event_dict,
        # 将来自 asgi-correlation-id 的 request_id 添加到所有日志事件
        add_request_id_to_event_dict,
    ]

    # 如果需要文件信息，则添加调用位置参数
    if include_file_info:
        processors.append(
            structlog.processors.CallsiteParameterAdder(
                {
                    structlog.processors.CallsiteParameter.FILENAME,
                    structlog.processors.CallsiteParameter.FUNC_NAME,
                    structlog.processors.CallsiteParameter.LINENO,
                    structlog.processors.CallsiteParameter.MODULE,
                    structlog.processors.CallsiteParameter.PATHNAME,
                }
            )
        )

    # 添加环境信息
    processors.append(lambda _, __, event_dict: {**event_dict, "environment": settings.ENVIRONMENT.value})

    return processors


def setup_logging() -> None:
    """根据环境使用不同的格式化器配置 structlog.

    开发环境：友好的控制台输出.
    预发布和生产环境：结构化 JSON 日志.
    """
    # 根据 DEBUG 配置确定日志级别
    log_level = logging.DEBUG if settings.DEBUG else logging.INFO

    # 创建 JSON 日志文件处理器
    file_handler = JsonlFileHandler(get_log_file_path())
    file_handler.setLevel(log_level)

    # 创建控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(log_level)

    # 获取共用处理器
    shared_processors = get_structlog_processors(
        # 仅在开发和测试环境中包含详细文件信息
        include_file_info=settings.ENVIRONMENT in [Environment.DEVELOPMENT, Environment.TEST]
    )

    # 配置标准日志
    logging.basicConfig(
        format="%(message)s",
        level=log_level,
        handlers=[file_handler, console_handler],
    )

    # 根据环境配置 structlog
    if settings.LOG_FORMAT == "console":
        # 适合开发环境的控制台日志
        structlog.configure(
            processors=[
                *shared_processors,
                # 使用 ConsoleRenderer 输出友好的控制台日志
                structlog.dev.ConsoleRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )
    else:
        # 生产环境 JSON 日志
        structlog.configure(
            processors=[
                *shared_processors,
                structlog.processors.JSONRenderer(),
            ],
            wrapper_class=structlog.stdlib.BoundLogger,
            logger_factory=structlog.stdlib.LoggerFactory(),
            cache_logger_on_first_use=True,
        )


# 初始化日志
setup_logging()

# 创建日志实例
logger = structlog.get_logger()
log_level_name = "DEBUG" if settings.DEBUG else "INFO"
logger.info(
    "logging_initialized",
    environment=settings.ENVIRONMENT.value,
    log_level=log_level_name,
    log_format=settings.LOG_FORMAT,
    debug=settings.DEBUG,
)
