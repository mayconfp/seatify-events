"""Rotas do modulo de autenticacao.

Thin routers: recebem request, injetam dependencias, chamam service
e retornam response. Zero logica de negocio aqui.
"""

from fastapi import APIRouter, Depends, Request
from fastapi.security import OAuth2PasswordRequestForm

from src.deps import LoggedUserDep, SessionDep, limiter
from src.module.auth import service
from src.module.auth.schemas import (
    LoginSchema,
    RegisterSchema,
    TokenResponseSchema,
    UserResponseSchema,
)
from src.util.jwt_utils import create_access_token

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/register", response_model=TokenResponseSchema, status_code=201)
@limiter.limit("30/minute")
async def register(
    request: Request, schema: RegisterSchema, session: SessionDep
) -> TokenResponseSchema:
    """Registra um novo usuario CLIENT e retorna JWT."""
    user = await service.register_user(session, schema)
    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponseSchema(access_token=token)


@router.post("/login", response_model=TokenResponseSchema)
@limiter.limit("60/minute")
async def login(
    request: Request,
    session: SessionDep,
    form_data: OAuth2PasswordRequestForm = Depends(),
) -> TokenResponseSchema:
    """Autentica usuario via OAuth2 form (username=email, password).

    Compativel com Swagger UI /docs — o campo 'username' recebe o email.
    """
    schema = LoginSchema(email=form_data.username, password=form_data.password)
    user = await service.authenticate_user(session, schema)
    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponseSchema(access_token=token)


@router.get("/me", response_model=UserResponseSchema)
async def get_current_user_info(user: LoggedUserDep) -> UserResponseSchema:
    """Retorna os dados do usuario autenticado."""
    return UserResponseSchema.model_validate(user)
