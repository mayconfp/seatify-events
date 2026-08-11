"""Rotas do modulo de eventos.

Thin routers para CRUD de eventos, mapa de assentos e busca no TMDb.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, Response

from src.deps import SessionDep, limiter, require_role
from src.module.auth.model import User, UserRole
from src.module.events import service
from src.module.tickets.service import _release_expired_pending_seats
from src.module.events.schemas import (
    CreateEventSchema,
    EventAnalyticsResponseSchema,
    EventListResponseSchema,
    EventResponseSchema,
    SeatResponseSchema,
    TmdbMovieSchema,
    TmdbSearchResponseSchema,
    TmdbTrendingResponseSchema,
    UpdateEventSchema,
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


@router.get("/tmdb/trending", response_model=TmdbTrendingResponseSchema)
@limiter.limit("60/minute")
async def tmdb_trending(
    request: Request,
    time_window: str = Query("week", description="Janela de tempo: 'day' ou 'week'"),
) -> TmdbTrendingResponseSchema:
    """Retorna filmes em alta no TMDb (publico)."""
    return await service.get_tmdb_trending(time_window)


@router.get("/tmdb/movie/{tmdb_id}", response_model=TmdbMovieSchema)
@limiter.limit("60/minute")
async def tmdb_movie_details(
    request: Request,
    tmdb_id: int,
    _organizer: OrganizerDep,
) -> TmdbMovieSchema:
    """Retorna detalhes de um filme do TMDb com generos e classificacao etaria BR (apenas ORGANIZER)."""
    return await service.get_tmdb_movie_details(tmdb_id)


@router.get("/organizer/me", response_model=EventListResponseSchema)
async def list_my_events(
    session: SessionDep,
    organizer: OrganizerDep,
    page: int = Query(1, ge=1, description="Numero da pagina (1-indexado)"),
    page_size: int = Query(
        20, ge=1, le=100, description="Itens por pagina (maximo 100)"
    ),
) -> EventListResponseSchema:
    """Lista eventos do organizador autenticado (apenas ORGANIZER)."""
    events, total = await service.list_organizer_events(
        session, organizer.id, page, page_size
    )
    return EventListResponseSchema(
        events=[EventResponseSchema.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


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


@router.get("/{event_id}/analytics", response_model=EventAnalyticsResponseSchema)
async def get_event_analytics(
    event_id: UUID,
    session: SessionDep,
    organizer: OrganizerDep,
) -> EventAnalyticsResponseSchema:
    """Retorna relatorio de ocupacao e faturamento de um evento (apenas ORGANIZER dono)."""
    return await service.get_event_analytics(session, organizer.id, event_id)


@router.get("", response_model=EventListResponseSchema)
@limiter.limit("120/minute")
async def list_events(
    request: Request,
    session: SessionDep,
    search: str | None = Query(None, description="Filtro por titulo"),
    genre: str | None = Query(None, description="Filtro por genero"),
    page: int = Query(1, ge=1, description="Numero da pagina (1-indexado)"),
    page_size: int = Query(
        20, ge=1, le=100, description="Itens por pagina (maximo 100)"
    ),
) -> EventListResponseSchema:
    """Lista eventos paginados (publico). Suporta busca por titulo e genero."""
    events, total = await service.list_events(session, search, genre, page, page_size)
    return EventListResponseSchema(
        events=[EventResponseSchema.model_validate(e) for e in events],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{event_id}", response_model=EventResponseSchema)
@limiter.limit("120/minute")
async def get_event(
    request: Request,
    event_id: UUID,
    session: SessionDep,
) -> EventResponseSchema:
    """Retorna detalhes de um evento (publico)."""
    event = await service.get_event_by_id(session, event_id)
    return EventResponseSchema.model_validate(event)


@router.get("/{event_id}/seats", response_model=list[SeatResponseSchema])
@limiter.limit("120/minute")
async def get_event_seats(
    request: Request,
    event_id: UUID,
    session: SessionDep,
    background_tasks: BackgroundTasks,
) -> list[SeatResponseSchema]:
    """Retorna mapa de assentos de um evento (publico).
    
    Apos retornar a resposta, engatilha limpeza de assentos expirados
    em background (sem bloquear o cliente).
    """
    seats = await service.get_event_seats(session, event_id)
    
    # Se houver assentos pendentes que ja passaram de 10 min, eles travam
    # a visualizacao. O ideal e que um worker faca isso, mas aqui disparamos
    # sob demanda como fallback se o worker estiver atrasado.
    background_tasks.add_task(_release_expired_pending_seats, session, event_id)
    return [SeatResponseSchema.model_validate(s) for s in seats]


@router.put("/{event_id}", response_model=EventResponseSchema)
async def update_event(
    event_id: UUID,
    schema: UpdateEventSchema,
    session: SessionDep,
    organizer: OrganizerDep,
) -> EventResponseSchema:
    """Atualiza um evento existente (apenas ORGANIZER dono)."""
    event = await service.update_organizer_event(session, organizer.id, event_id, schema)
    return EventResponseSchema.model_validate(event)


@router.delete("/{event_id}", status_code=204)
async def delete_event(
    event_id: UUID,
    session: SessionDep,
    organizer: OrganizerDep,
) -> Response:
    """Exclui um evento (soft-delete) se nao houver ingressos vendidos (apenas ORGANIZER dono)."""
    await service.delete_organizer_event(session, organizer.id, event_id)
    return Response(status_code=204)

