"""应用会话模型."""

from typing import (
    TYPE_CHECKING,
    Optional,
)

from sqlmodel import (
    Field,
    Relationship,
)

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.user import User


class Session(BaseModel, table=True):
    """用于保存聊天会话的模型.

    字段：
        id: 主键.
        user_id: 用户外键.
        name: 会话名称，默认为空字符串.
        username: 创建会话时从用户复制的显示名称.
        created_at: 会话创建时间.
        messages: 与会话消息的关联关系.
        user: 与会话所属用户的关联关系.
    """

    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str = Field(default="")
    username: Optional[str] = Field(default=None)
    user: "User" = Relationship(back_populates="sessions")
