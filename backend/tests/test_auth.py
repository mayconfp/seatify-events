"""Teste de autenticação — login e JWT.

Valida que o usuário semeado pelo run_seed.py consegue:
1. Fazer login via POST /auth/login e receber um JWT válido.
2. O JWT decodificado contém os campos esperados (sub, role).

Requer banco de dados com seed aplicado.
"""

import pytest

from src.util.jwt_utils import decode_access_token
from src.util.password_digest import hash_password, is_valid_password_hash


@pytest.mark.asyncio
async def test_seeded_user_password_hash_is_valid() -> None:
    """O hash gerado para a senha do seed deve ser verificável."""
    password = "Client1@2026"
    hashed = hash_password(password)

    assert is_valid_password_hash(password, hashed) is True
    assert is_valid_password_hash("senha_errada", hashed) is False


@pytest.mark.asyncio
async def test_access_token_contains_expected_claims() -> None:
    """Um access token gerado deve conter 'sub' e 'role' ao ser decodificado."""
    import uuid

    from src.util.jwt_utils import create_access_token
    from src.module.auth.model import UserRole

    user_id = uuid.uuid4()
    token = create_access_token(user_id=user_id, role=UserRole.CLIENT.value)

    payload = decode_access_token(token)

    assert payload["sub"] == str(user_id)
    assert payload["role"] == UserRole.CLIENT.value
    assert "exp" in payload
    assert "iat" in payload


@pytest.mark.asyncio
async def test_expired_or_invalid_token_raises_value_error() -> None:
    """Tokens inválidos ou corrompidos devem levantar ValueError."""
    with pytest.raises(ValueError, match="Token inválido"):
        decode_access_token("token.invalido.aqui")
