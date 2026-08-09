"""Schemas Pydantic v2 do modulo de autenticacao.

DTOs de entrada e resposta para registro, login e consulta de usuario.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field

from src.module.auth.model import UserRole


class RegisterSchema(BaseModel):
    """Payload para criacao de novo usuario (CLIENT)."""

    name: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)


class LoginSchema(BaseModel):
    """Payload para autenticacao via email e senha."""

    email: EmailStr
    password: str


class TokenResponseSchema(BaseModel):
    """Resposta de autenticacao compativel com OAuth2 RFC."""

    access_token: str
    token_type: str = "bearer"


class UserResponseSchema(BaseModel):
    """Representacao publica de um usuario."""

    id: UUID
    name: str
    email: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}
