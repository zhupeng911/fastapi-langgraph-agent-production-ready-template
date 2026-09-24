"""所有接口共用的基础响应 Schema."""

from uuid import UUID, uuid4

from asgi_correlation_id import correlation_id
from pydantic import BaseModel, Field


def _get_request_id() -> UUID:
    """返回当前请求的关联 ID；不存在时生成新的 UUID 作为兜底."""
    value = correlation_id.get()
    return UUID(value) if value else uuid4()


class BaseResponse(BaseModel):
    """所有接口响应继承的基础响应模型.

    request_id 会从 CorrelationIdMiddleware 的 ContextVar 自动填充，接口无需显式传入.
    """

    request_id: UUID = Field(default_factory=_get_request_id, description="Unique identifier for this request")
