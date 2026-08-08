"""Fixtures compartilhadas para testes de integração.

O AsyncClient do httpx aponta para app de src/main.py usando
ASGITransport — sem abrir sockets reais, testando a stack FastAPI completa.
"""

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from src.main import app


@pytest_asyncio.fixture
async def client() -> AsyncClient:
    """Cliente HTTP assíncrono conectado à aplicação via ASGI."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://testserver",
    ) as ac:
        yield ac
