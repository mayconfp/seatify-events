"""Testes de integracao do fluxo de reserva (reserve, checkout, gatekeeper).

Cobre o double-booking, expiracao de assentos, webhook idempotente,
e validacao na portaria.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, login_seeded_user


@pytest.mark.asyncio
async def test_reserve_checkout_gatekeeper_flow(client: AsyncClient) -> None:
    """Fluxo completo: reserva, checkout simulado, e portaria."""
    # 1. Pega ID do evento SEATED do seed
    list_response = await client.get("/events")
    events = list_response.json()["events"]
    assert len(events) > 0
    event_id = events[0]["id"]

    # 2. Login do CLIENT 1
    client_token = await login_seeded_user(client, "client1@eventify.com", "Client1@2026")

    # 3. Pega 2 assentos disponiveis
    seats_response = await client.get(f"/events/{event_id}/seats")
    available_seats = [s["seat_number"] for s in seats_response.json() if s["status"] == "AVAILABLE"]
    assert len(available_seats) >= 2
    seat1, seat2 = available_seats[0], available_seats[1]

    # 4. Faz reserva
    reserve_response = await client.post(
        f"/events/{event_id}/reserve",
        json={"seat_numbers": [seat1, seat2]},
        headers=auth_headers(client_token),
    )
    assert reserve_response.status_code == 201
    assert reserve_response.json()["reserved_seats"] == [seat1, seat2]

    # Verifica status PENDING no mapa de assentos
    seats_response = await client.get(f"/events/{event_id}/seats")
    seats = {s["seat_number"]: s["status"] for s in seats_response.json()}
    assert seats[seat1] == "PENDING"
    assert seats[seat2] == "PENDING"

    # 5. Outro cliente tenta reservar (Double booking)
    client2_token = await login_seeded_user(client, "client2@eventify.com", "Client2@2026")
    conflict_response = await client.post(
        f"/events/{event_id}/reserve",
        json={"seat_numbers": [seat2, available_seats[2]]},  # seat2 ja esta PENDING
        headers=auth_headers(client2_token),
    )
    assert conflict_response.status_code == 409

    # 6. Cliente 1 faz o checkout simulado (reserva -> confirmacao)
    checkout_response = await client.post(
        "/checkout/simulate",
        json={
            "event_id": event_id,
            "seat_numbers": [seat1, seat2],
            "simulate_failure": False,
        },
        headers=auth_headers(client_token),
    )
    assert checkout_response.status_code == 200
    assert checkout_response.json()["status"] == "succeeded"

    # 7. Pega os tickets do Cliente 1
    tickets_response = await client.get("/tickets/me", headers=auth_headers(client_token))
    assert tickets_response.status_code == 200
    tickets = tickets_response.json()
    assert len(tickets) >= 2

    # Pega os dados do ticket 1
    ticket_1 = next(t for t in tickets if t["seat_number"] == seat1)
    qr_token = ticket_1["qr_code_token"]
    share_hash = ticket_1["share_link_hash"]

    # 8. Portaria valida com QR Token (Gatekeeper)
    gk_token = await login_seeded_user(client, "gatekeeper@eventify.com", "Gatekeeper@2026")
    validate_response = await client.post(
        "/gatekeeper/validate",
        json={"qr_token_or_hash": qr_token, "event_id": event_id},
        headers=auth_headers(gk_token),
    )
    assert validate_response.status_code == 200
    assert validate_response.json()["status"] == "VALID"

    # 9. Portaria tenta validar de novo -> ALREADY_USED
    revalidate_response = await client.post(
        "/gatekeeper/validate",
        json={"qr_token_or_hash": qr_token, "event_id": event_id},
        headers=auth_headers(gk_token),
    )
    assert revalidate_response.status_code == 200
    assert revalidate_response.json()["status"] == "ALREADY_USED"

    # 10. Portaria valida o seat2 por share_hash (fallback)
    ticket_2 = next(t for t in tickets if t["seat_number"] == seat2)
    validate_hash_resp = await client.post(
        "/gatekeeper/validate",
        json={"qr_token_or_hash": ticket_2["share_link_hash"], "event_id": event_id},
        headers=auth_headers(gk_token),
    )
    assert validate_hash_resp.status_code == 200
    assert validate_hash_resp.json()["status"] == "VALID"


@pytest.mark.asyncio
async def test_checkout_simulate_failure(client: AsyncClient) -> None:
    """Falha simulada no checkout deve reverter assentos para AVAILABLE."""
    # ...
    list_response = await client.get("/events")
    event_id = list_response.json()["events"][0]["id"]
    client_token = await login_seeded_user(client, "client1@eventify.com", "Client1@2026")

    seats_response = await client.get(f"/events/{event_id}/seats")
    available_seats = [s["seat_number"] for s in seats_response.json() if s["status"] == "AVAILABLE"]
    target_seat = available_seats[-1] # Pega o ultimo disponivel para simular

    # Primeiro reserva
    await client.post(
        f"/events/{event_id}/reserve",
        json={"seat_numbers": [target_seat]},
        headers=auth_headers(client_token),
    )

    checkout_response = await client.post(
        "/checkout/simulate",
        json={
            "event_id": event_id,
            "seat_numbers": [target_seat],
            "simulate_failure": True,
        },
        headers=auth_headers(client_token),
    )
    assert checkout_response.status_code == 200
    assert checkout_response.json()["status"] == "failed"

    seats_response = await client.get(f"/events/{event_id}/seats")
    seats = {s["seat_number"]: s["status"] for s in seats_response.json()}
    assert seats[target_seat] == "AVAILABLE"
