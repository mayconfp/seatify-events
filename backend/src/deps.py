"""Dependências FastAPI injetáveis nas rotas.

Padrões:
- Funções get_* são dependências FastAPI (async generators ou callables).
- Aliases *Dep são os únicos que os handlers devem importar — escondem
  o wiring e produzem anotações de tipo corretas.
- require_role() é uma factory que retorna uma dependência para RBAC.
"""

import logging
from collections.abc import AsyncGenerator
from typing import Annotated
from uuid import UUID

import jwt
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.session import get_session
from src.errors.router import forbidden_error, not_found_error, unauthorized_error
from src.module.auth.model import User, UserRole
from src.util.jwt_utils import decode_access_token

logger = logging.getLogger("eventify.deps")

# Session

SessionDep = Annotated[AsyncSession, Depends(get_session)]

# Auth

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


async def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: SessionDep,
) -> User:
    """Decodifica o Bearer JWT e retorna o User correspondente.

    Raises:
        401: token ausente, expirado ou com assinatura inválida.
        404: usuário do token não existe mais no banco.
    """
    try:
        payload = decode_access_token(token)
    except ValueError as exc:
        raise unauthorized_error(str(exc)) from exc

    raw_id: str | None = payload.get("sub")
    if raw_id is None:
        raise unauthorized_error("Token sem campo 'sub'")

    try:
        user_id = UUID(raw_id)
    except ValueError as exc:
        raise unauthorized_error("Token com 'sub' inválido") from exc

    user = await session.get(User, user_id)
    if user is None or user.deleted_at is not None:
        raise not_found_error("Usuário não encontrado")

    return user


LoggedUserDep = Annotated[User, Depends(get_current_user)]


# RBAC


def require_role(allowed_roles: list[UserRole]):
    """Factory de dependência para controle de acesso baseado em papel (RBAC).

    Uso no handler:
        @router.get("/admin", dependencies=[Depends(require_role([UserRole.ORGANIZER]))])

    Ou como parâmetro tipado:
        async def endpoint(user: LoggedUserDep, _: Annotated[None, Depends(require_role([UserRole.ORGANIZER]))]):

    Args:
        allowed_roles: lista de papéis que têm acesso à rota.

    Returns:
        Dependência FastAPI que levanta 403 se o papel do usuário não estiver
        na lista.
    """

    async def _check_role(current_user: LoggedUserDep) -> User:
        if current_user.role not in allowed_roles:
            raise forbidden_error(
                f"Acesso restrito a: {', '.join(r.value for r in allowed_roles)}"
            )
        return current_user

    return _check_role
