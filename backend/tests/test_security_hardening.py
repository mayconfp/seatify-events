"""Testes de hardening de seguranca da API.

Valida:
1. Presenca dos cabecalhos HTTP de seguranca OWASP em todas as respostas
   (incluindo respostas de erro).
2. Politica de CORS restrita a settings.frontend_url.
3. Validacao de entropia/comprimento de segredos criticos no startup.
"""

import uuid

import pytest
from httpx import AsyncClient

from src.core.config import settings, validate_critical_secrets
from src.main import SECURITY_HEADERS


# ── Security headers OWASP ─────────────────────────────────────────────────────

EXPECTED_HEADERS = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'self'",
    "X-XSS-Protection": "1; mode=block",
}


def test_security_headers_constant_matches_owasp_baseline() -> None:
    """A constante SECURITY_HEADERS deve conter exatamente os 5 cabecalhos."""
    assert SECURITY_HEADERS == EXPECTED_HEADERS


@pytest.mark.asyncio
async def test_security_headers_present_on_success_response(
    client: AsyncClient,
) -> None:
    """GET /healthz deve retornar todos os cabecalhos de seguranca."""
    response = await client.get("/healthz")
    assert response.status_code == 200
    for header_name, header_value in EXPECTED_HEADERS.items():
        assert response.headers.get(header_name) == header_value


@pytest.mark.asyncio
async def test_security_headers_present_on_error_response(
    client: AsyncClient,
) -> None:
    """Respostas de erro (404) tambem devem carregar os cabecalhos."""
    response = await client.get(f"/events/{uuid.uuid4()}")
    assert response.status_code == 404
    for header_name, header_value in EXPECTED_HEADERS.items():
        assert response.headers.get(header_name) == header_value


# ── CORS restrito ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_cors_allows_configured_frontend_origin(client: AsyncClient) -> None:
    """Preflight com a origem do front-end configurada deve ser aceito."""
    response = await client.options(
        "/healthz",
        headers={
            "Origin": settings.frontend_url,
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert (
        response.headers.get("access-control-allow-origin")
        == settings.frontend_url
    )


@pytest.mark.asyncio
async def test_cors_blocks_unknown_origin(client: AsyncClient) -> None:
    """Preflight com origem desconhecida nao deve receber allow-origin."""
    response = await client.options(
        "/healthz",
        headers={
            "Origin": "https://malicioso.example.com",
            "Access-Control-Request-Method": "GET",
        },
    )
    # CORSMiddleware responde 400 para preflight de origem nao permitida
    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


# ── Validacao de segredos criticos ─────────────────────────────────────────────

_STRONG_SECRET = "kJ8mN2pQ7rT4vW9xA3bC6dE1fG5hL0zY"  # 32 chars, sem termos fracos


def _settings_with(jwt_secret_key: str, fernet_secret: str):
    """Retorna uma copia das settings com os segredos substituidos."""
    return settings.model_copy(
        update={
            "jwt_secret_key": jwt_secret_key,
            "fernet_secret": fernet_secret,
        }
    )


def test_validate_critical_secrets_accepts_strong_secrets() -> None:
    """Segredos com 32+ caracteres e sem termos fracos devem passar."""
    validate_critical_secrets(
        _settings_with(_STRONG_SECRET, _STRONG_SECRET[::-1])
    )


def test_validate_critical_secrets_rejects_short_secret() -> None:
    """Segredo com menos de 32 caracteres deve abortar o startup."""
    with pytest.raises(RuntimeError, match="jwt_secret_key"):
        validate_critical_secrets(_settings_with("curto", _STRONG_SECRET))


@pytest.mark.parametrize(
    "weak_value",
    [
        "secret" + "x" * 30,
        "x" * 30 + "123456",
        "prefixo_change_me_sufixo_grande_ok",
        "SuperSECRETKeyMuitoGrandePara32chars",
    ],
)
def test_validate_critical_secrets_rejects_weak_terms(weak_value: str) -> None:
    """Segredos contendo termos padrao fracos devem abortar o startup."""
    with pytest.raises(RuntimeError, match="termos fracos"):
        validate_critical_secrets(_settings_with(weak_value, _STRONG_SECRET))


def test_validate_critical_secrets_reports_all_problems_at_once() -> None:
    """Multiplos problemas devem ser reportados na mesma excecao."""
    with pytest.raises(RuntimeError) as exc_info:
        validate_critical_secrets(_settings_with("123456", "change_me"))
    message = str(exc_info.value)
    assert "jwt_secret_key" in message
    assert "fernet_secret" in message


def test_validate_critical_secrets_never_leaks_secret_value() -> None:
    """A mensagem de erro nunca deve conter o valor do segredo."""
    leaked_secret = "change_me_valor_sensivel_do_segredo_12345"
    with pytest.raises(RuntimeError) as exc_info:
        validate_critical_secrets(_settings_with(leaked_secret, _STRONG_SECRET))
    assert leaked_secret not in str(exc_info.value)
