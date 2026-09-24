"""应用线程模型."""

from datetime import (
    UTC,
    datetime,
)

from sqlmodel import (
    Field,
    SQLModel,
)


class Thread(SQLModel, table=True):
    """用于保存会话线程的模型.

    字段：
        id: 主键.
        created_at: 线程创建时间.
        messages: 与线程消息的关联关系.
    """

    id: str = Field(primary_key=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
