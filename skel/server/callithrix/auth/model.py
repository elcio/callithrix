from pydantic import BaseModel, Field, EmailStr, SecretStr
from typing import Optional, ClassVar


class MelBase(BaseModel):
    id: Optional[int] = None
    class Config:
        audit_table = 'user'


class User(MelBase):
    name: str = Field(max_length=128, example="John Doe", notnull=True)
    email: EmailStr = Field(max_length=128, example="john.doe@email.com", unique=True, notnull=True)
    password: SecretStr = Field(max_length=128, example="Password173_A@ttt")
    validation_code: Optional[str] = Field(max_length=128, example="123456", internal=True, default='')
    recovery_code: Optional[str] = Field(max_length=128, example="123456", internal=True, default='')
    def __str__(self):
        return f'{self.name} ({self.email})'
    priority: ClassVar = 1000


class Permission(MelBase):
    name: str = Field(max_length=128, example="manage_users", unique=True, notnull=True)
    def __str__(self):
        return self.name


class Role(MelBase):
    name: str = Field(max_length=128, example="admin", unique=True, notnull=True)
    def __str__(self):
        return self.name


class RolePermission(MelBase):
    role_id: int
    permission_id: int


class UserRole(MelBase):
    user_id: int
    role_id: int

