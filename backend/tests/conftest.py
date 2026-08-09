"""Fixtures compartilhadas para testes de integracao.

O AsyncClient do httpx aponta para app de src/main.py usando
ASGITransport — sem abrir sockets reais, testando a stack FastAPI completa.

Inclui helpers para registro e login de usuarios durante os testes.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Cliente HTTP assincrono conectado a aplicacao via ASGI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac


async def register_and_login(
    client: AsyncClient,
    name: str,
    email: str,
    password: str,
) -> str:
    """Helper: registra um usuario e retorna o access_token."""
    await client.post(
        "/auth/register",
        json={"name": name, "email": email, "password": password},
    )
    response = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    return response.json()["access_token"]


async def login_seeded_user(client: AsyncClient, email: str, password: str) -> str:
    """Helper: faz login com um usuario do seed e retorna o access_token."""
    response = await client.post(
        "/auth/login",
        data={"username": email, "password": password},
    )
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    """Helper: retorna headers de autorizacao Bearer."""
    return {"Authorization": f"Bearer {token}"}
