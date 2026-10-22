"""认证相关请求/响应模型（中心版）。

登录标识支持邮箱、学号、手机号任一；咨询师/管理员账号不由本接口创建。
"""

import re
import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator, model_validator

from app.core.roles import Role

USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9_\-\u4e00-\u9fa5]{2,50}$")
STUDENT_NO_PATTERN = re.compile(r"^[A-Za-z0-9\-]{2,32}$")
PHONE_PATTERN = re.compile(r"^\+?[0-9]{6,20}$")


class RegisterRequest(BaseModel):
    """学生注册请求：邮箱/学号/手机号至少一个，密码与隐私同意必填。"""

    email: EmailStr | None = None
    student_no: str | None = Field(default=None, max_length=32)
    phone: str | None = Field(default=None, max_length=20)
    password: str = Field(min_length=8, max_length=128)
    username: str | None = Field(default=None, min_length=2, max_length=50)
    # 必须显式勾选：隐私说明 + 非医疗免责声明
    privacy_accepted: bool

    @field_validator("student_no")
    @classmethod
    def _validate_student_no(cls, value: str | None) -> str | None:
        """去空白；空串按未填写处理；格式不符则报错。"""
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not STUDENT_NO_PATTERN.fullmatch(value):
            raise ValueError("学号需为 2-32 位字母、数字或连字符")
        return value

    @field_validator("phone")
    @classmethod
    def _validate_phone(cls, value: str | None) -> str | None:
        """去掉空格与连字符后校验；空串按未填写处理。"""
        if value is None:
            return None
        value = value.replace(" ", "").replace("-", "")
        if not value:
            return None
        if not PHONE_PATTERN.fullmatch(value):
            raise ValueError("手机号格式不正确")
        return value

    @field_validator("username")
    @classmethod
    def _validate_username(cls, value: str | None) -> str | None:
        """用户名去除首尾空白；空串按未填写处理，格式不符则报错。"""
        if value is None:
            return None
        value = value.strip()
        if not value:
            return None
        if not USERNAME_PATTERN.fullmatch(value):
            raise ValueError("用户名需为 2-50 位中文、字母、数字、下划线或连字符")
        return value

    @model_validator(mode="after")
    def _require_identity_and_privacy(self) -> "RegisterRequest":
        """校验至少一个登录标识，且隐私说明与非医疗免责声明已勾选。"""
        if not (self.email or self.student_no or self.phone):
            raise ValueError("邮箱、学号、手机号至少填写一个")
        if not self.privacy_accepted:
            raise ValueError("必须阅读并同意隐私说明与非医疗免责声明")
        return self


class LoginRequest(BaseModel):
    """登录请求：identifier 为邮箱/学号/手机号；email 字段保留兼容旧客户端。"""

    identifier: str | None = Field(default=None, max_length=255)
    email: EmailStr | None = None
    password: str = Field(min_length=1, max_length=128)

    @model_validator(mode="after")
    def _require_identity(self) -> "LoginRequest":
        """校验至少提供 identifier 或 email。"""
        if not self.identifier and not self.email:
            raise ValueError("请填写邮箱、学号或手机号")
        return self


class UserRead(BaseModel):
    """用户响应：可见的个人资料字段，不含密码。"""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    email: EmailStr | None
    username: str | None
    role: Role
    student_no: str | None
    phone: str | None
    created_at: datetime


class TokenResponse(BaseModel):
    """令牌响应：JWT 访问令牌及其类型。"""

    access_token: str
    token_type: Literal["bearer"] = "bearer"


class AuthResponse(TokenResponse):
    """认证响应：令牌加当前用户信息，用于注册与登录。"""

    user: UserRead
