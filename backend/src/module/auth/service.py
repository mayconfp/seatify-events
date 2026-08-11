"""Camada de negocio do modulo de autenticacao.

Toda regra de negocio relacionada a registro e login reside aqui.
Os routers chamam estas funcoes e nunca acessam o banco diretamente.
"""

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.errors.router import conflict_error, unauthorized_error
from src.module.auth.model import User, UserRole
from src.module.auth.schemas import RegisterSchema, LoginSchema
from src.util.password_digest import hash_password, is_valid_password_hash

logger = logging.getLogger("eventify.auth.service")


def _mask_email(email: str) -> str:
    """Mascara o email para logs de auditoria."""
    local_part, _, domain = email.partition("@")
    visible = local_part[:2] if len(local_part) > 2 else local_part[:1]
    return f"{visible}***@{domain}"


async def register_user(session: AsyncSession, schema: RegisterSchema) -> User:
    """Registra um novo usuario com papel CLIENT.

    Verifica unicidade do email antes de inserir.

    Args:
        session: sessao async do banco.
        schema: dados de registro validados pelo Pydantic.

    Returns:
        User recem-criado (ja com id populado via flush).

    Raises:
        409 Conflict: email ja cadastrado.
    """
    result = await session.execute(
        select(User).where(User.email == schema.email)
    )
    if result.scalar_one_or_none() is not None:
        raise conflict_error("Email ja cadastrado")

    user = User(
        name=schema.name,
        email=schema.email,
        password_digest=hash_password(schema.password),
        role=UserRole.CLIENT,
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def authenticate_user(session: AsyncSession, schema: LoginSchema) -> User:
    """Autentica um usuario por email e senha.

    Args:
        session: sessao async do banco.
        schema: credenciais de login.

    Returns:
        User autenticado.

    Raises:
        401 Unauthorized: email nao encontrado ou senha incorreta.
    """
    result = await session.execute(
        select(User).where(User.email == schema.email)
    )
    user = result.scalar_one_or_none()

    if user is None or user.deleted_at is not None:
        # Auditoria: tentativa de login com email desconhecido/desativado.
        # Nunca logar a senha informada.
        logger.warning(
            "Falha de autenticacao: email desconhecido ou desativado (%s)",
            _mask_email(schema.email),
        )
        raise unauthorized_error("Email ou senha incorretos")

    if not is_valid_password_hash(schema.password, user.password_digest):
        # Auditoria: senha incorreta para usuario existente.
        logger.warning(
            "Falha de autenticacao: senha incorreta (user_id=%s, email=%s)",
            user.id,
            _mask_email(schema.email),
        )
        raise unauthorized_error("Email ou senha incorretos")

    logger.info("Login bem-sucedido (user_id=%s, role=%s)", user.id, user.role.value)
    return user
