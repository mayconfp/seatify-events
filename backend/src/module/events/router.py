"""Rotas do modulo de eventos.

Thin handlers para CRUD de eventos, mapa de assentos e busca no TMDb.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request

from src.deps import SessionDep, limiter, require_role
from src.module.auth.model import User, UserRole
from src.module.events import service
from src.module.events.schemas import (
    CreateEventSchema,
    EventListResponseSchema,
    EventResponseSchema,
    SeatResponseSchema,
    TmdbSearchResponseSchema,
)

router = APIRouter(prefix="/events", tags=["Events"])

OrganizerDep = Annotated[User, Depends(require_role([UserRole.ORGANIZER]))]


@router.get("/tmdb/search", response_model=TmdbSearchResponseSchema)
@limiter.limit("60/minute")
async def search_tmdb(
    request: Request,
    _organizer: OrganizerDep,
    query: str = Query(..., min_length=1, description="Texto de busca no TMDb"),
) -> TmdbSearchResponseSchema:
    """Busca filmes na API do TMDb (apenas ORGANIZER)."""
    return await service.search_tmdb_movies(query)


@router.post("", response_model=EventResponseSchema, status_code=201)
async def create_event(
    schema: CreateEventSchema,
    session: SessionDep,
    organizer: OrganizerDep,
) -> EventResponseSchema:
    """Cria um novo evento (apenas ORGANIZER).

    Se o tipo for SEATED, assentos sao criados automaticamente.
    """
    event = await service.create_event(session, organizer, schema)
    return EventResponseSchema.model_validate(event)


@router.get("", response_model=EventListResponseSchema)
async def list_events(
    session: SessionDep,
    search: str | None = Query(None, description="Filtro por titulo"),
    page: int = Query(1, ge=1, description="Numero da pagina (1-indexado)"),
    page_size: int = Query(
        20, ge=1, le=100, description="Itens por pagina (maximo 100)"
    ),
) -> EventListResponseSchema:
    """Lista eventos paginados (publico). Suporta busca por titulo."""
    events, total = await service.list_events(session, search, page, page_size)
    return EventListResponseSchema(
        events=[EventResponseSchema.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{event_id}", response_model=EventResponseSchema)
async def get_event(
    event_id: UUID,
    session: SessionDep,
) -> EventResponseSchema:
    """Retorna detalhes de um evento (publico)."""
    event = await service.get_event_by_id(session, event_id)
    return EventResponseSchema.model_validate(event)


@router.get("/{event_id}/seats", response_model=list[SeatResponseSchema])
async def get_event_seats(
    event_id: UUID,
    session: SessionDep,
) -> list[SeatResponseSchema]:
    """Retorna mapa de assentos de um evento (publico)."""
    seats = await service.get_event_seats(session, event_id)
    return [SeatResponseSchema.model_validate(s) for s in seats]
