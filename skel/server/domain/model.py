from pydantic import BaseModel, Field, EmailStr, SecretStr
from typing import Optional


class MelBase(BaseModel):
    id: Optional[int] = None
    class Config:
        audit_table = 'user'

