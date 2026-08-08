"""Teste de saúde da API.

Valida que GET /healthz retorna 200 OK com payload {"status": "ok"}.
Este teste não requer banco de dados — apenas verifica que a aplicação
FastAPI sobe e responde ao endpoint de health check.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_healthz_returns_200_ok(client: AsyncClient) -> None:
    """GET /healthz deve retornar 200 OK com status 'ok'."""
    response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
