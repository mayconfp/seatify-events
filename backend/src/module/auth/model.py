"""Modelo ORM do módulo de autenticação.

Define o enum de papéis e a entidade `User`. Todos os perfis necessários
ao Eventify estão presentes: ORGANIZER, CLIENT e GATEKEEPER.
"""

import enum

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

from src.db.base import BaseModel, varchar_enum


class UserRole(str, enum.Enum):
    """Papéis disponíveis na plataforma.

    - ORGANIZER: cria e gerencia eventos.
    - CLIENT: compra ingressos e gerencia reservas.
    - GATEKEEPER: valida QR Codes na entrada dos eventos (portaria).
    """

    ORGANIZER = "ORGANIZER"
    CLIENT = "CLIENT"
    GATEKEEPER = "GATEKEEPER"


class User(BaseModel):
    """Usuário da plataforma.

    O campo password_digest armazena o hash PBKDF2-SHA256 no formato
    salt_hex$hash_hex - nunca a senha em plaintext.
    """

    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_digest: Mapped[str] = mapped_column(String(512), nullable=False)
    role: Mapped[UserRole] = mapped_column(
        varchar_enum(UserRole, name="user_role"),
        nullable=False,
    )
