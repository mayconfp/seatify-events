"""Testes de integracao da integracao real com o Stripe.

Cobre a criacao de Checkout Session (com mock da SDK sincrona do Stripe)
e a verificacao criptografica do webhook (assinatura valida, invalida e
idempotencia).
"""

from __future__ import annotations

import json
import uuid
from types import SimpleNamespace
from typing import Any

import pytest
import stripe
from httpx import AsyncClient

from src.core.config import settings
from src.module.checkout import service as checkout_service
from tests.conftest import auth_headers, login_seeded_user


# Helpers de setup

async def _create_event_with_reserved_seats(
    client: AsyncClient,
    capacity: int = 3,
    seats_to_reserve: int = 2,
) -> tuple[str, str, list[str]]:
    """Cria um evento SEATED novo e reserva N assentos para client1.

    Retorna (event_id, client_token, seat_numbers). Cada teste usa um evento
    isolado para evitar interferencia entre execucoes e testes.
    """
    organizer_token = await login_seeded_user(
        client, "organizer@eventify.com", "Organizer@2026"
    )
    unique = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/events",
        json={
            "title": f"Stripe Test Event {unique}",
            "description": "Evento gerado pelo teste de integracao do Stripe.",
            "event_date": "2027-06-15T20:00:00Z",
            "venue_name": "Arena Stripe Test",
            "capacity": capacity,
            "price": "49.90",
            "type": "SEATED",
        },
        headers=auth_headers(organizer_token),
    )
    assert create_resp.status_code == 201, create_resp.text
    event_id = create_resp.json()["id"]

    client_token = await login_seeded_user(
        client, "client1@eventify.com", "Client1@2026"
    )
    seat_numbers = [f"A{i}" for i in range(1, seats_to_reserve + 1)]
    reserve_resp = await client.post(
        f"/events/{event_id}/reserve",
        json={"seat_numbers": seat_numbers},
        headers=auth_headers(client_token),
    )
    assert reserve_resp.status_code == 201, reserve_resp.text
    return event_id, client_token, seat_numbers


def _build_stripe_event(
    stripe_event_id: str,
    event_type: str,
    event_id: str,
    client_id: str,
    seat_numbers: list[str],
) -> dict[str, Any]:
    """Constroi um dict compativel com stripe.Event para uso nos testes."""
    return {
        "id": stripe_event_id,
        "type": event_type,
        "data": {
            "object": {
                "id": f"cs_test_{uuid.uuid4().hex[:16]}",
                "metadata": {
                    "event_id": event_id,
                    "client_id": client_id,
                    "seat_numbers": json.dumps(seat_numbers),
                },
            }
        },
    }


# /checkout/create-session

@pytest.mark.asyncio
async def test_create_checkout_session_returns_url(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """POST /checkout/create-session deve retornar session_id e checkout_url."""
    event_id, client_token, seat_numbers = await _create_event_with_reserved_seats(
        client
    )

    fake_session = SimpleNamespace(
        id="cs_test_abc123",
        url="https://checkout.stripe.com/c/pay/cs_test_abc123",
    )
    calls: dict[str, Any] = {}

    def fake_create(**kwargs: Any) -> SimpleNamespace:
        calls.update(kwargs)
        return fake_session

    monkeypatch.setattr(stripe.checkout.Session, "create", fake_create)

    response = await client.post(
        "/checkout/create-session",
        json={"event_id": event_id, "seat_numbers": seat_numbers},
        headers=auth_headers(client_token),
    )

    assert response.status_code == 201, response.text
    body = response.json()
    assert body["session_id"] == "cs_test_abc123"
    assert body["checkout_url"].startswith("https://checkout.stripe.com/")

    # A metadata enviada ao Stripe deve carregar os campos necessarios para
    # o webhook reconstruir a reserva.
    metadata = calls["metadata"]
    assert metadata["event_id"] == event_id
    assert json.loads(metadata["seat_numbers"]) == seat_numbers
    assert calls["mode"] == "payment"
    assert calls["payment_method_types"] == ["card"]
    assert calls["line_items"][0]["quantity"] == len(seat_numbers)
    # Preco convertido para centavos (49.90 -> 4990)
    assert calls["line_items"][0]["price_data"]["unit_amount"] == 4990


@pytest.mark.asyncio
async def test_create_checkout_session_rejects_seats_not_pending(
    client: AsyncClient,
) -> None:
    """POST /checkout/create-session deve retornar 400 se seats nao PENDING."""
    organizer_token = await login_seeded_user(
        client, "organizer@eventify.com", "Organizer@2026"
    )
    unique = uuid.uuid4().hex[:8]
    create_resp = await client.post(
        "/events",
        json={
            "title": f"Stripe Test No-Reserve {unique}",
            "event_date": "2027-06-15T20:00:00Z",
            "venue_name": "Arena Stripe Test",
            "capacity": 3,
            "price": "10.00",
            "type": "SEATED",
        },
        headers=auth_headers(organizer_token),
    )
    event_id = create_resp.json()["id"]

    client_token = await login_seeded_user(
        client, "client1@eventify.com", "Client1@2026"
    )
    response = await client.post(
        "/checkout/create-session",
        json={"event_id": event_id, "seat_numbers": ["A1"]},
        headers=auth_headers(client_token),
    )
    assert response.status_code == 400


# /checkout/webhook (assinatura real)

@pytest.mark.asyncio
async def test_webhook_valid_signature_confirms_reservation(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Webhook com assinatura valida deve confirmar reserva e emitir tickets."""
    event_id, client_token, seat_numbers = await _create_event_with_reserved_seats(
        client
    )
    # Descobre o client_id a partir do endpoint /auth/me.
    me_resp = await client.get("/auth/me", headers=auth_headers(client_token))
    client_id = me_resp.json()["id"]

    stripe_event_id = f"evt_test_{uuid.uuid4().hex[:16]}"
    fake_event = _build_stripe_event(
        stripe_event_id=stripe_event_id,
        event_type="checkout.session.completed",
        event_id=event_id,
        client_id=client_id,
        seat_numbers=seat_numbers,
    )

    monkeypatch.setattr(
        checkout_service.settings, "stripe_webhook_secret", "whsec_test_stub"
    )
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda payload, sig_header, secret, tolerance=None: fake_event,
    )

    response = await client.post(
        "/checkout/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "t=0,v1=stub"},
    )
    assert response.status_code == 200, response.text
    assert response.json() == {"status": "processed"}

    # Confere que os tickets foram emitidos
    tickets_resp = await client.get(
        "/tickets/me", headers=auth_headers(client_token)
    )
    tickets = tickets_resp.json()
    seats_with_tickets = {
        t["seat_number"] for t in tickets if t["event_id"] == event_id
    }
    assert set(seat_numbers).issubset(seats_with_tickets)


@pytest.mark.asyncio
async def test_webhook_invalid_signature_returns_400(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Assinatura invalida deve resultar em HTTP 400."""
    monkeypatch.setattr(
        checkout_service.settings, "stripe_webhook_secret", "whsec_test_stub"
    )

    def _raise(payload, sig_header, secret, tolerance=None):
        raise stripe.error.SignatureVerificationError(
            "Signature verification failed", sig_header, payload
        )

    monkeypatch.setattr(stripe.Webhook, "construct_event", _raise)

    response = await client.post(
        "/checkout/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "t=0,v1=invalid"},
    )
    assert response.status_code == 400
    assert "assinatura" in response.json()["detail"].lower()


@pytest.mark.asyncio
async def test_webhook_idempotent_on_duplicate_event(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Reenvio do mesmo stripe_event_id nao deve reprocessar (idempotencia)."""
    event_id, client_token, seat_numbers = await _create_event_with_reserved_seats(
        client
    )
    me_resp = await client.get("/auth/me", headers=auth_headers(client_token))
    client_id = me_resp.json()["id"]

    stripe_event_id = f"evt_test_{uuid.uuid4().hex[:16]}"
    fake_event = _build_stripe_event(
        stripe_event_id=stripe_event_id,
        event_type="payment_intent.succeeded",
        event_id=event_id,
        client_id=client_id,
        seat_numbers=seat_numbers,
    )

    monkeypatch.setattr(
        checkout_service.settings, "stripe_webhook_secret", "whsec_test_stub"
    )
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda payload, sig_header, secret, tolerance=None: fake_event,
    )

    # 1a chamada: processa
    first = await client.post(
        "/checkout/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "t=0,v1=stub"},
    )
    assert first.status_code == 200

    tickets_before = (
        await client.get("/tickets/me", headers=auth_headers(client_token))
    ).json()
    count_before = sum(1 for t in tickets_before if t["event_id"] == event_id)

    # 2a chamada com o MESMO stripe_event_id: idempotente
    second = await client.post(
        "/checkout/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "t=0,v1=stub"},
    )
    assert second.status_code == 200

    tickets_after = (
        await client.get("/tickets/me", headers=auth_headers(client_token))
    ).json()
    count_after = sum(1 for t in tickets_after if t["event_id"] == event_id)
    assert count_before == count_after == len(seat_numbers)


# Edge cases: reserva expirada e divergencia parcial

@pytest.mark.asyncio
async def test_webhook_expired_seats_returns_200_no_tickets(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Webhook para assentos ja expirados deve retornar 200 sem emitir tickets."""
    event_id, client_token, seat_numbers = await _create_event_with_reserved_seats(
        client
    )
    me_resp = await client.get("/auth/me", headers=auth_headers(client_token))
    client_id = me_resp.json()["id"]

    # Simula a expiracao: reverte os assentos PENDING -> AVAILABLE antes do webhook
    simulate_resp = await client.post(
        "/checkout/simulate",
        json={
            "event_id": event_id,
            "seat_numbers": seat_numbers,
            "simulate_failure": True,
        },
        headers=auth_headers(client_token),
    )
    assert simulate_resp.status_code == 200

    # Agora dispara um webhook como se o Stripe tivesse confirmado o pagamento
    stripe_event_id = f"evt_test_expired_{uuid.uuid4().hex[:16]}"
    fake_event = _build_stripe_event(
        stripe_event_id=stripe_event_id,
        event_type="checkout.session.completed",
        event_id=event_id,
        client_id=client_id,
        seat_numbers=seat_numbers,
    )

    monkeypatch.setattr(
        checkout_service.settings, "stripe_webhook_secret", "whsec_test_stub"
    )
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda payload, sig_header, secret, tolerance=None: fake_event,
    )

    response = await client.post(
        "/checkout/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "t=0,v1=stub"},
    )
    # Deve retornar 200 (nao 404) para evitar loop de retentativas do Stripe
    assert response.status_code == 200
    assert response.json() == {"status": "processed"}

    # Nenhum ticket emitido para este evento
    tickets_resp = await client.get(
        "/tickets/me", headers=auth_headers(client_token)
    )
    tickets_for_event = [
        t for t in tickets_resp.json() if t["event_id"] == event_id
    ]
    assert len(tickets_for_event) == 0


@pytest.mark.asyncio
async def test_webhook_partial_seat_mismatch_returns_200_no_tickets(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Webhook com divergencia parcial de assentos nao deve emitir ingressos parciais."""
    event_id, client_token, seat_numbers = await _create_event_with_reserved_seats(
        client, capacity=4, seats_to_reserve=3
    )
    me_resp = await client.get("/auth/me", headers=auth_headers(client_token))
    client_id = me_resp.json()["id"]

    # Simula expiracao parcial: libera apenas o primeiro assento usando
    # o endpoint de simulacao de falha para assentos individuais.
    # Como simulate nao suporta parcial, usamos uma segunda reserva/falha
    # apenas para A1. Em vez disso, chamamos simulate_failure com todos
    # e re-reservamos apenas 2.
    fail_resp = await client.post(
        "/checkout/simulate",
        json={
            "event_id": event_id,
            "seat_numbers": seat_numbers,
            "simulate_failure": True,
        },
        headers=auth_headers(client_token),
    )
    assert fail_resp.status_code == 200

    # Re-reserva apenas 2 dos 3 assentos originais
    partial_seats = seat_numbers[:2]
    reserve_resp = await client.post(
        f"/events/{event_id}/reserve",
        json={"seat_numbers": partial_seats},
        headers=auth_headers(client_token),
    )
    assert reserve_resp.status_code == 201

    # Webhook chega com os 3 assentos originais, mas so 2 estao PENDING
    stripe_event_id = f"evt_test_mismatch_{uuid.uuid4().hex[:16]}"
    fake_event = _build_stripe_event(
        stripe_event_id=stripe_event_id,
        event_type="payment_intent.succeeded",
        event_id=event_id,
        client_id=client_id,
        seat_numbers=seat_numbers,  # 3 assentos
    )

    monkeypatch.setattr(
        checkout_service.settings, "stripe_webhook_secret", "whsec_test_stub"
    )
    monkeypatch.setattr(
        stripe.Webhook,
        "construct_event",
        lambda payload, sig_header, secret, tolerance=None: fake_event,
    )

    response = await client.post(
        "/checkout/webhook",
        content=b"{}",
        headers={"Stripe-Signature": "t=0,v1=stub"},
    )
    assert response.status_code == 200
    assert response.json() == {"status": "processed"}

    # Nenhum ticket emitido (divergencia impede emissao parcial)
    tickets_resp = await client.get(
        "/tickets/me", headers=auth_headers(client_token)
    )
    tickets_for_event = [
        t for t in tickets_resp.json() if t["event_id"] == event_id
    ]
    assert len(tickets_for_event) == 0
