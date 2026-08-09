"""Camada de negocio do modulo de eventos.

Responsabilidades: criacao de eventos com geracao automatica de assentos,
listagem/busca, consulta de mapa de assentos e integracao com TMDb.
"""

import logging
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.errors.router import not_found_error, validation_error
from src.module.auth.model import User
from src.module.events.model import Event, EventType
from src.module.events.schemas import (
    CreateEventSchema,
    TmdbMovieSchema,
    TmdbSearchResponseSchema,
)
from src.module.tickets.model import Seat, SeatStatus

logger = logging.getLogger("eventify.events.service")


async def search_tmdb_movies(query: str) -> TmdbSearchResponseSchema:
    """Busca filmes na API do TMDb.

    Usa httpx.AsyncClient com Bearer token para consumir a API.

    Args:
        query: texto de busca (titulo do filme).

    Returns:
        TmdbSearchResponseSchema com a lista de resultados.
    """
    if not query or not query.strip():
        raise validation_error("O campo 'query' nao pode estar vazio")

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.tmdb_base_url}/search/movie",
            params={"query": query, "language": "pt-BR", "page": 1},
            headers={
                "Authorization": f"Bearer {settings.tmdb_read_token}",
                "Accept": "application/json",
            },
            timeout=10.0,
        )

    if response.status_code != 200:
        logger.warning("TMDb retornou status %d: %s", response.status_code, response.text)
        raise validation_error("Erro ao consultar TMDb. Tente novamente.")

    data = response.json()
    movies = [
        TmdbMovieSchema(
            id=item["id"],
            title=item.get("title", ""),
            overview=item.get("overview"),
            poster_path=item.get("poster_path"),
            release_date=item.get("release_date"),
        )
        for item in data.get("results", [])
    ]
    return TmdbSearchResponseSchema(
        results=movies,
        total_results=data.get("total_results", 0),
    )


async def create_event(
    session: AsyncSession,
    organizer: User,
    schema: CreateEventSchema,
) -> Event:
    """Cria um evento e, se SEATED, gera assentos automaticamente.

    Args:
        session: sessao async do banco.
        organizer: usuario ORGANIZER autenticado.
        schema: dados do evento validados pelo Pydantic.

    Returns:
        Event recem-criado com id populado.
    """
    event = Event(
        organizer_id=organizer.id,
        title=schema.title,
        description=schema.description,
        event_date=schema.event_date,
        venue_name=schema.venue_name,
        capacity=schema.capacity,
        price=schema.price,
        type=schema.type,
        external_tmdb_id=schema.external_tmdb_id,
        poster_url=schema.poster_url,
    )
    session.add(event)
    await session.flush()

    # Se SEATED, cria assentos com numeracao A1, A2, ..., A{capacity}
    if schema.type == EventType.SEATED:
        seats = [
            Seat(
                event_id=event.id,
                seat_number=f"A{i}",
                status=SeatStatus.AVAILABLE,
            )
            for i in range(1, schema.capacity + 1)
        ]
        session.add_all(seats)

    await session.commit()
    await session.refresh(event)
    return event


async def list_events(
    session: AsyncSession,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Event], int]:
    """Lista eventos paginados com filtro opcional por titulo.

    aplicando LIMIT/OFFSET diretamente na query do banco.

    Args:
        session: sessao async do banco.
        search: texto para filtro ILIKE no titulo (opcional).
        page: numero da pagina (1-indexado).
        page_size: quantidade de itens por pagina.

    Returns:
        Tupla (lista de eventos da pagina, total geral de eventos).
    """
    query = select(Event).where(Event.deleted_at.is_(None))
    count_query = select(func.count()).select_from(Event).where(Event.deleted_at.is_(None))

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(Event.title.ilike(pattern))
        count_query = count_query.where(Event.title.ilike(pattern))

    query = (
        query.order_by(Event.event_date.asc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )

    result = await session.execute(query)
    events = list(result.scalars().all())

    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    return events, total


async def get_event_by_id(session: AsyncSession, event_id: UUID) -> Event:
    """Busca um evento pelo UUID.

    Args:
        session: sessao async do banco.
        event_id: UUID do evento.

    Returns:
        Event encontrado.

    Raises:
        404: evento nao encontrado ou soft-deleted.
    """
    event = await session.get(Event, event_id)
    if event is None or event.deleted_at is not None:
        raise not_found_error("Evento nao encontrado")
    return event


async def get_event_seats(session: AsyncSession, event_id: UUID) -> list[Seat]:
    """Retorna todos os assentos de um evento com seus status.

    Assentos em PENDING ha mais de 15 minutos sao tratados como
    AVAILABLE para exibicao (a liberacao efetiva ocorre na reserva).

    Args:
        session: sessao async do banco.
        event_id: UUID do evento.

    Returns:
        Lista de Seat do evento.

    Raises:
        404: evento nao encontrado.
    """
    # Valida que o evento existe
    await get_event_by_id(session, event_id)

    result = await session.execute(
        select(Seat)
        .where(Seat.event_id == event_id, Seat.deleted_at.is_(None))
        .order_by(Seat.seat_number.asc())
    )
    return list(result.scalars().all())
