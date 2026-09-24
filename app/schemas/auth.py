"""应用认证相关 Schema."""

import re
from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
    SecretStr,
    field_validator,
)

from app.schemas.base import BaseResponse


class Token(BaseModel):
    """用于认证的令牌模型.

    字段：
        access_token: JWT 访问令牌.
        token_type: 令牌类型，始终为 "bearer".
        expires_at: 令牌过期时间.
    """

    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field(default="bearer", description="The type of token")
    expires_at: datetime = Field(..., description="The token expiration timestamp")


class TokenResponse(BaseResponse):
    """登录接口的响应模型.

    字段：
        access_token: JWT 访问令牌.
        token_type: 令牌类型，始终为 "bearer".
        expires_at: 令牌过期时间.
    """

    access_token: str = Field(..., description="The JWT access token")
    token_type: str = Field(default="bearer", description="The type of token")
    expires_at: datetime = Field(..., description="When the token expires")


class UserCreate(BaseModel):
    """用户注册请求模型.

    字段：
        email: 用户邮箱地址.
        password: 用户密码.
        username: 可选的显示名称.
    """

    email: EmailStr = Field(..., description="User's email address")
    password: SecretStr = Field(..., description="User's password", min_length=8, max_length=64)
    username: str | None = Field(default=None, description="Optional display name", max_length=50)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: SecretStr) -> SecretStr:
        """校验密码强度.

        参数：
            v: 待校验的密码.

        返回：
            SecretStr: 校验通过的密码.

        异常：
            ValueError: 密码强度不足时抛出.
        """
        password = v.get_secret_value()

        # 检查密码是否满足常见安全要求
        if len(password) < 8:
            raise ValueError("Password must be at least 8 characters long")

        if not re.search(r"[A-Z]", password):
            raise ValueError("Password must contain at least one uppercase letter")

        if not re.search(r"[a-z]", password):
            raise ValueError("Password must contain at least one lowercase letter")

        if not re.search(r"[0-9]", password):
            raise ValueError("Password must contain at least one number")

        if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
            raise ValueError("Password must contain at least one special character")

        return v


class UserResponse(BaseResponse):
    """用户相关操作的响应模型.

    字段：
        id: 用户 ID.
        email: 用户邮箱地址.
        username: 可选的显示名称.
        token: 认证令牌.
    """

    id: int = Field(..., description="User's ID")
    email: str = Field(..., description="User's email address")
    username: str | None = Field(default=None, description="Optional display name")
    token: Token = Field(..., description="Authentication token")


class SessionResponse(BaseResponse):
    """会话创建接口的响应模型.

    字段：
        session_id: 聊天会话的唯一标识.
        name: 会话名称，默认为空字符串.
        token: 会话认证令牌.
    """

    session_id: str = Field(..., description="The unique identifier for the chat session")
    name: str = Field(default="", description="Name of the session", max_length=100)
    token: Token = Field(..., description="The authentication token for the session")

    @field_validator("name")
    @classmethod
    def sanitize_name(cls, v: str) -> str:
        """清理会话名称.

        参数：
            v: 待清理的名称.

        返回：
            str: 清理后的名称.
        """
        # 移除可能有害的字符
        sanitized = re.sub(r'[<>{}[\]()\'"`]', "", v)
        return sanitized
