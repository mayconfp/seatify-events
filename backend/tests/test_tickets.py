"""Teste de assinatura e decodificação do QR Code.

Valida que:
1. create_qr_token() gera um JWT assinado contendo ticket_id e event_id.
2. decode_qr_token() recupera os UUIDs originais.
3. Um token adulterado é rejeitado com ValueError.
4. Um token de acesso comum é rejeitado como QR token (sub diferente).

Estes testes não requerem banco de dados — apenas as funções criptográficas.
"""

import uuid

import pytest

from src.util.jwt_utils import (
    create_access_token,
    create_qr_token,
    decode_qr_token,
)
from src.module.auth.model import UserRole


@pytest.mark.asyncio
async def test_qr_token_contains_ticket_and_event_ids() -> None:
    """O QR token deve conter ticket_id e event_id originais ao decodificar."""
    ticket_id = uuid.uuid4()
    event_id = uuid.uuid4()

    token = create_qr_token(ticket_id=ticket_id, event_id=event_id)
    payload = decode_qr_token(token)

    assert payload["ticket_id"] == str(ticket_id)
    assert payload["event_id"] == str(event_id)
    assert payload["sub"] == "qr_ticket"


@pytest.mark.asyncio
async def test_tampered_qr_token_raises_value_error() -> None:
    """Um QR token adulterado (assinatura inválida) deve levantar ValueError."""
    ticket_id = uuid.uuid4()
    event_id = uuid.uuid4()

    token = create_qr_token(ticket_id=ticket_id, event_id=event_id)
    # Adulterar o payload (segunda parte do JWT)
    parts = token.split(".")
    tampered = parts[0] + ".ADULTERADO" + "." + parts[2]

    with pytest.raises(ValueError, match="QR Code token inválido"):
        decode_qr_token(tampered)


@pytest.mark.asyncio
async def test_access_token_rejected_as_qr_token() -> None:
    """Um access token válido não deve ser aceito como QR token."""
    user_id = uuid.uuid4()
    access_token = create_access_token(user_id=user_id, role=UserRole.CLIENT.value)

    # O access token tem sub != "qr_ticket", deve ser rejeitado
    with pytest.raises(ValueError, match="Token não é um QR Code válido"):
        decode_qr_token(access_token)


@pytest.mark.asyncio
async def test_qr_token_ids_are_stable_across_decodes() -> None:
    """Decodificações repetidas do mesmo token retornam os mesmos IDs."""
    ticket_id = uuid.uuid4()
    event_id = uuid.uuid4()

    token = create_qr_token(ticket_id=ticket_id, event_id=event_id)

    payload_1 = decode_qr_token(token)
    payload_2 = decode_qr_token(token)

    assert payload_1["ticket_id"] == payload_2["ticket_id"] == str(ticket_id)
    assert payload_1["event_id"] == payload_2["event_id"] == str(event_id)
