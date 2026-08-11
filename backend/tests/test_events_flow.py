"""Testes de integracao do fluxo de eventos.

Cobre criacao de evento SEATED com geracao automatica de assentos,
listagem publica e busca por titulo.
"""

import pytest
from httpx import AsyncClient

from tests.conftest import auth_headers, login_seeded_user


@pytest.mark.asyncio
async def test_create_event_seated(client: AsyncClient) -> None:
    """POST /events como ORGANIZER deve criar evento e assentos."""
    token = await login_seeded_user(client, "organizer@eventify.com", "Organizer@2026")

    response = await client.post(
        "/events",
        json={
            "title": "Show de Teste API",
            "description": "Evento criado via teste de integracao",
            "event_date": "2026-12-25T20:00:00Z",
            "venue_name": "Arena Teste",
            "capacity": 5,
            "price": "49.90",
            "type": "SEATED",
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "Show de Teste API"
    assert data["capacity"] == 5
    assert data["type"] == "SEATED"

    # Verifica que os assentos foram criados
    event_id = data["id"]
    seats_response = await client.get(f"/events/{event_id}/seats")
    assert seats_response.status_code == 200
    seats = seats_response.json()
    assert len(seats) == 5
    assert seats[0]["seat_number"] == "A1"
    assert seats[0]["status"] == "AVAILABLE"


@pytest.mark.asyncio
async def test_create_event_past_date_rejected(client: AsyncClient) -> None:
    """POST /events com event_date no passado deve retornar 400."""
    token = await login_seeded_user(client, "organizer@eventify.com", "Organizer@2026")

    response = await client.post(
        "/events",
        json={
            "title": "Show no Passado",
            "event_date": "2020-01-01T20:00:00Z",
            "venue_name": "Arena Teste",
            "capacity": 5,
            "price": "49.90",
            "type": "SEATED",
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 400


@pytest.mark.asyncio
async def test_update_event_owner_success(client: AsyncClient) -> None:
    """PUT /events/{id} pelo organizador dono deve atualizar os campos."""
    token = await login_seeded_user(client, "organizer@eventify.com", "Organizer@2026")

    create_response = await client.post(
        "/events",
        json={
            "title": "Show Original",
            "event_date": "2026-12-25T20:00:00Z",
            "venue_name": "Arena Original",
            "capacity": 5,
            "price": "49.90",
            "type": "SEATED",
        },
        headers=auth_headers(token),
    )
    event_id = create_response.json()["id"]

    update_response = await client.put(
        f"/events/{event_id}",
        json={"title": "Show Atualizado", "venue_name": "Arena Nova"},
        headers=auth_headers(token),
    )
    assert update_response.status_code == 200
    data = update_response.json()
    assert data["title"] == "Show Atualizado"
    assert data["venue_name"] == "Arena Nova"
    assert data["capacity"] == 5


@pytest.mark.asyncio
async def test_update_event_past_date_rejected(client: AsyncClient) -> None:
    """PUT /events/{id} com nova data no passado deve retornar 400."""
    token = await login_seeded_user(client, "organizer@eventify.com", "Organizer@2026")

    create_response = await client.post(
        "/events",
        json={
            "title": "Show para Atualizar",
            "event_date": "2026-12-25T20:00:00Z",
            "venue_name": "Arena Teste",
            "capacity": 5,
            "price": "49.90",
            "type": "SEATED",
        },
        headers=auth_headers(token),
    )
    event_id = create_response.json()["id"]

    update_response = await client.put(
        f"/events/{event_id}",
        json={"event_date": "2020-01-01T20:00:00Z"},
        headers=auth_headers(token),
    )
    assert update_response.status_code == 400


@pytest.mark.asyncio
async def test_update_event_non_owner_forbidden(client: AsyncClient) -> None:
    """PUT /events/{id} por outro organizador deve retornar 403."""
    owner_token = await login_seeded_user(client, "organizer@eventify.com", "Organizer@2026")

    create_response = await client.post(
        "/events",
        json={
            "title": "Show Protegido",
            "event_date": "2026-12-25T20:00:00Z",
            "venue_name": "Arena Teste",
            "capacity": 5,
            "price": "49.90",
            "type": "SEATED",
        },
        headers=auth_headers(owner_token),
    )
    event_id = create_response.json()["id"]

    client_token = await login_seeded_user(client, "client1@eventify.com", "Client1@2026")
    update_response = await client.put(
        f"/events/{event_id}",
        json={"title": "Tentativa Invasora"},
        headers=auth_headers(client_token),
    )
    assert update_response.status_code == 403


@pytest.mark.asyncio
async def test_create_event_client_forbidden(client: AsyncClient) -> None:
    """POST /events como CLIENT deve retornar 403."""
    token = await login_seeded_user(client, "client1@eventify.com", "Client1@2026")

    response = await client.post(
        "/events",
        json={
            "title": "Nao deveria funcionar",
            "event_date": "2026-12-25T20:00:00Z",
            "venue_name": "Arena",
            "capacity": 10,
            "price": "25.00",
            "type": "PISTA",
        },
        headers=auth_headers(token),
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_list_events_public(client: AsyncClient) -> None:
    """GET /events sem autenticacao deve retornar lista publica paginada."""
    response = await client.get("/events")
    assert response.status_code == 200
    data = response.json()
    assert "events" in data
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] >= 1  # Pelo menos o evento do seed


@pytest.mark.asyncio
async def test_list_events_pagination(client: AsyncClient) -> None:
    """GET /events com page/page_size deve aplicar LIMIT/OFFSET."""
    response = await client.get("/events", params={"page": 1, "page_size": 1})
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 1
    assert len(data["events"]) <= 1


@pytest.mark.asyncio
async def test_list_events_pagination_invalid(client: AsyncClient) -> None:
    """GET /events com page_size acima do limite deve retornar 422."""
    response = await client.get("/events", params={"page_size": 101})
    assert response.status_code == 422

    response = await client.get("/events", params={"page": 0})
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_events_search(client: AsyncClient) -> None:
    """GET /events?search= deve filtrar por titulo."""
    response = await client.get("/events", params={"search": "Eventify Music"})
    assert response.status_code == 200
    data = response.json()
    # O evento do seed contem "Eventify Music Fest" no titulo
    assert data["total"] >= 1
    assert "Eventify" in data["events"][0]["title"]


@pytest.mark.asyncio
async def test_get_event_by_id(client: AsyncClient) -> None:
    """GET /events/{id} deve retornar detalhes do evento."""
    # Primeiro lista para pegar um ID valido
    list_response = await client.get("/events")
    events = list_response.json()["events"]
    assert len(events) > 0

    event_id = events[0]["id"]
    response = await client.get(f"/events/{event_id}")
    assert response.status_code == 200
    assert response.json()["id"] == event_id


@pytest.mark.asyncio
async def test_get_event_not_found(client: AsyncClient) -> None:
    """GET /events/{id} com UUID inexistente deve retornar 404."""
    import uuid

    fake_id = str(uuid.uuid4())
    response = await client.get(f"/events/{fake_id}")
    assert response.status_code == 404
