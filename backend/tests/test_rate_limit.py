"""Testes isolados do rate limiting (SlowAPI).

Valida:
1. O wiring do limiter na aplicacao real (app.state.limiter e handler 429).
2. O comportamento funcional de bloqueio HTTP 429 em uma app isolada,
   sem poluir o orcamento de requisicoes das rotas reais nem depender do banco.
3. Que a rota de webhook do checkout NAO possui rate limit aplicado.
"""

import pytest
from fastapi import FastAPI, Request
from httpx import ASGITransport, AsyncClient
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from src.deps import limiter
from src.main import app


def test_app_has_limiter_configured() -> None:
    """A aplicacao real deve expor o limiter em app.state e ser um Limiter."""
    assert isinstance(limiter, Limiter)
    assert getattr(app.state, "limiter", None) is limiter


def test_rate_limit_exceeded_handler_registered() -> None:
    """O handler de RateLimitExceeded deve estar registrado na app real."""
    assert RateLimitExceeded in app.exception_handlers


def test_expected_routes_are_rate_limited() -> None:
    """As 6 rotas exigidas devem estar registradas no limiter._route_limits."""
    limited_keys = set(limiter._route_limits.keys())
    expected = {
        "src.module.auth.handler.register",
        "src.module.auth.handler.login",
        "src.module.events.handler.search_tmdb",
        "src.module.tickets.handler.reserve_seats",
        "src.module.checkout.handler.simulate_payment",
        "src.module.gatekeeper.handler.validate_entry",
    }
    assert expected.issubset(limited_keys)


def test_webhook_route_has_no_rate_limit() -> None:
    """A rota POST /checkout/webhook NAO deve possuir rate limit."""
    limited_keys = set(limiter._route_limits.keys())
    assert "src.module.checkout.handler.receive_webhook" not in limited_keys
    assert not any("webhook" in key for key in limited_keys)


@pytest.mark.asyncio
async def test_limiter_blocks_after_threshold() -> None:
    """Uma rota isolada com limite baixo deve retornar 429 ao exceder."""
    isolated_limiter = Limiter(key_func=get_remote_address)
    isolated_app = FastAPI()
    isolated_app.state.limiter = isolated_limiter
    isolated_app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    @isolated_app.get("/ping")
    @isolated_limiter.limit("2/minute")
    async def ping(request: Request) -> dict[str, str]:  # pyright: ignore[reportUnusedFunction]
        return {"status": "ok"}

    async with AsyncClient(
        transport=ASGITransport(app=isolated_app),
        base_url="http://testserver",
    ) as ac:
        first = await ac.get("/ping")
        second = await ac.get("/ping")
        third = await ac.get("/ping")

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 429
