"""Testes de integracao do fluxo de autenticacao.

Cobre registro, login, acesso autenticado e erros de validacao.
"""

import uuid
import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, login_seeded_user, register_and_login


@pytest.mark.asyncio
async def test_register_new_user(client: AsyncClient) -> None:
    """POST /auth/register deve criar um usuario CLIENT e retornar JWT."""
    unique_email = f"test_register_{uuid.uuid4().hex[:8]}@eventify.com"
    response = await client.post(
        "/auth/register",
        json={
            "name": "Teste Registro",
            "email": unique_email,
            "password": "Senha@Forte123",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_register_duplicate_email(client: AsyncClient) -> None:
    """POST /auth/register com email duplicado deve retornar 409."""
    # Usa usuario do seed que ja existe
    response = await client.post(
        "/auth/register",
        json={
            "name": "Duplicado",
            "email": "organizer@eventify.com",
            "password": "Senha@Forte123",
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_login_seeded_organizer(client: AsyncClient) -> None:
    """POST /auth/login com credenciais do seed deve retornar JWT."""
    response = await client.post(
        "/auth/login",
        data={"username": "organizer@eventify.com", "password": "Organizer@2026"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient) -> None:
    """POST /auth/login com senha errada deve retornar 401."""
    response = await client.post(
        "/auth/login",
        data={"username": "organizer@eventify.com", "password": "SenhaErrada"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_email(client: AsyncClient) -> None:
    """POST /auth/login com email inexistente deve retornar 401."""
    response = await client.post(
        "/auth/login",
        data={"username": "inexistente@eventify.com", "password": "Qualquer123"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_me_authenticated(client: AsyncClient) -> None:
    """GET /auth/me com token valido deve retornar dados do usuario."""
    token = await login_seeded_user(client, "organizer@eventify.com", "Organizer@2026")
    response = await client.get("/auth/me", headers=auth_headers(token))

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "organizer@eventify.com"
    assert data["role"] == "ORGANIZER"
    assert "id" in data
    assert "name" in data


@pytest.mark.asyncio
async def test_get_me_without_token(client: AsyncClient) -> None:
    """GET /auth/me sem token deve retornar 401."""
    response = await client.get("/auth/me")
    assert response.status_code == 401
