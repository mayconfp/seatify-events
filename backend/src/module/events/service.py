"""Camada de negocio do modulo de eventos.

Responsabilidades: criacao de eventos com geracao automatica de assentos,
listagem/busca, consulta de mapa de assentos e integracao com TMDb.
"""

import asyncio
import logging
from datetime import timedelta
from decimal import Decimal
from uuid import UUID

import httpx
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.errors.router import conflict_error, forbidden_error, not_found_error, validation_error
from src.module.auth.model import User
from src.module.events.model import Event, EventType
from src.module.events.schemas import (
    CreateEventSchema,
    EventAnalyticsResponseSchema,
    TmdbCastMemberSchema,
    TmdbMovieSchema,
    TmdbSearchResponseSchema,
    TmdbTrendingResponseSchema,
    UpdateEventSchema,
)
from src.module.tickets.model import Seat, SeatStatus, Ticket, TicketStatus
from src.util.datetime_utils import aware_utcnow, ensure_aware_utc

logger = logging.getLogger("eventify.events.service")

# Mapa estatico de genre_ids do TMDB -> nomes em pt-BR.
# Fonte: https://api.themoviedb.org/3/genre/movie/list?language=pt-BR
TMDB_GENRE_MAP: dict[int, str] = {
    28: "Ação",
    12: "Aventura",
    16: "Animação",
    35: "Comédia",
    80: "Crime",
    99: "Documentário",
    18: "Drama",
    10751: "Família",
    14: "Fantasia",
    36: "História",
    27: "Terror",
    10402: "Música",
    9648: "Mistério",
    10749: "Romance",
    878: "Ficção Científica",
    10770: "Cinema TV",
    53: "Suspense",
    10752: "Guerra",
    37: "Faroeste",
}

_TMDB_HEADERS = {
    "Accept": "application/json",
}


def _tmdb_auth_headers() -> dict[str, str]:
    return {**_TMDB_HEADERS, "Authorization": f"Bearer {settings.tmdb_read_token}"}


def _genre_ids_to_names(genre_ids: list[int]) -> list[str]:
    """Converte lista de genre_ids do TMDB em nomes pt-BR."""
    return [TMDB_GENRE_MAP[gid] for gid in genre_ids if gid in TMDB_GENRE_MAP]


async def _fetch_br_certification(tmdb_id: int) -> str | None:
    """Busca a classificacao etaria brasileira de um filme no TMDB.

    Consulta o endpoint /movie/{id}/release_dates e filtra pelo
    pais BR. Retorna a certificacao (ex: "14", "16", "L") ou None.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.tmdb_base_url}/movie/{tmdb_id}/release_dates",
            headers=_tmdb_auth_headers(),
            timeout=10.0,
        )
    if response.status_code != 200:
        logger.warning(
            "TMDb release_dates retornou %d para movie %d",
            response.status_code,
            tmdb_id,
        )
        return None

    for country in response.json().get("results", []):
        if country.get("iso_3166_1") == "BR":
            for rd in country.get("release_dates", []):
                cert = rd.get("certification", "").strip()
                if cert:
                    return cert
    return None


async def _fetch_credits(tmdb_id: int) -> tuple[str | None, list[TmdbCastMemberSchema]]:
    """Busca diretor e elenco principal de um filme no TMDB.

    Consulta /movie/{id}/credits, filtra crew por job=Director e
    retorna os primeiros 8 atores do cast principal.

    Returns:
        Tupla (nome_diretor, lista_de_atores).
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.tmdb_base_url}/movie/{tmdb_id}/credits",
            params={"language": "pt-BR"},
            headers=_tmdb_auth_headers(),
            timeout=10.0,
        )
    if response.status_code != 200:
        logger.warning(
            "TMDb credits retornou %d para movie %d",
            response.status_code,
            tmdb_id,
        )
        return None, []

    data = response.json()
    director: str | None = None
    for member in data.get("crew", []):
        if member.get("job") == "Director":
            director = member.get("name")
            break

    cast = [
        TmdbCastMemberSchema(
            name=actor["name"],
            character=actor.get("character"),
            profile_path=actor.get("profile_path"),
        )
        for actor in data.get("cast", [])[:8]
    ]
    return director, cast


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
            headers=_tmdb_auth_headers(),
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
            genres=_genre_ids_to_names(item.get("genre_ids", [])),
            vote_average=item.get("vote_average"),
            popularity=item.get("popularity"),
        )
        for item in data.get("results", [])
    ]
    return TmdbSearchResponseSchema(
        results=movies,
        total_results=data.get("total_results", 0),
    )


_trending_cache: dict[str, dict] = {}

async def get_tmdb_trending(
    time_window: str = "week",
) -> TmdbTrendingResponseSchema:
    """Retorna filmes em alta (trending) do TMDB com cache em memoria.

    Args:
        time_window: "day" ou "week".

    Returns:
        TmdbTrendingResponseSchema com filmes populares.
    """
    if time_window not in ("day", "week"):
        raise validation_error("time_window deve ser 'day' ou 'week'")

    now = aware_utcnow()
    
    # Verifica se existe cache valido 6 hrs
    cached = _trending_cache.get(time_window)
    if cached and cached["expires_at"] > now:
        return cached["data"]

    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.tmdb_base_url}/trending/movie/{time_window}",
            params={"language": "pt-BR"},
            headers=_tmdb_auth_headers(),
            timeout=10.0,
        )

    if response.status_code != 200:
        logger.warning("TMDb trending retornou status %d", response.status_code)
        raise validation_error("Erro ao consultar filmes em alta no TMDb.")

    data = response.json()
    movies = [
        TmdbMovieSchema(
            id=item["id"],
            title=item.get("title", ""),
            overview=item.get("overview"),
            poster_path=item.get("poster_path"),
            release_date=item.get("release_date"),
            genres=_genre_ids_to_names(item.get("genre_ids", [])),
            vote_average=item.get("vote_average"),
            popularity=item.get("popularity"),
        )
        for item in data.get("results", [])
        if item.get("media_type", "movie") == "movie"
    ]
    
    response_schema = TmdbTrendingResponseSchema(results=movies, time_window=time_window)
    
    # Salva no cache em memoria
    _trending_cache[time_window] = {
        "expires_at": now + timedelta(hours=6),
        "data": response_schema
    }
    
    return response_schema


async def get_tmdb_movie_details(tmdb_id: int) -> TmdbMovieSchema:
    """Busca detalhes completos de um filme no TMDB, incluindo classificacao etaria BR.

    Args:
        tmdb_id: ID do filme no TMDB.

    Returns:
        TmdbMovieSchema com generos e classificacao etaria.
    """
    async with httpx.AsyncClient() as client:
        response = await client.get(
            f"{settings.tmdb_base_url}/movie/{tmdb_id}",
            params={"language": "pt-BR"},
            headers=_tmdb_auth_headers(),
            timeout=10.0,
        )

    if response.status_code != 200:
        raise not_found_error(f"Filme TMDB {tmdb_id} nao encontrado")

    data = response.json()
    certification, (director, cast) = await asyncio.gather(
        _fetch_br_certification(tmdb_id),
        _fetch_credits(tmdb_id),
    )

    genres = [g["name"] for g in data.get("genres", [])]
    poster_path = data.get("poster_path")
    if poster_path and not poster_path.startswith("http"):
        poster_path = f"https://image.tmdb.org/t/p/w500{poster_path}"

    return TmdbMovieSchema(
        id=data["id"],
        title=data.get("title", ""),
        overview=data.get("overview"),
        poster_path=poster_path,
        release_date=data.get("release_date"),
        genres=genres,
        age_rating=certification,
        director=director,
        vote_average=data.get("vote_average"),
        popularity=data.get("popularity"),
        cast=cast,
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

    Raises:
        422: data do evento esta no passado.
    """
    if ensure_aware_utc(schema.event_date) < aware_utcnow():
        raise validation_error("A data e hora da sessao devem ser no futuro.")

    # Se tmdb_id fornecido e genero/classificacao/diretor nao preenchidos, busca do TMDB
    genre = schema.genre
    age_rating = schema.age_rating
    director = schema.director
    release_date = schema.release_date
    vote_average = schema.vote_average
    cast = schema.cast

    if schema.external_tmdb_id:
        try:
            tmdb_details = await get_tmdb_movie_details(int(schema.external_tmdb_id))
            if not genre and tmdb_details.genres:
                genre = ", ".join(tmdb_details.genres)
            if not age_rating and tmdb_details.age_rating:
                age_rating = tmdb_details.age_rating
            if not director and tmdb_details.director:
                director = tmdb_details.director
            if not release_date and tmdb_details.release_date:
                release_date = tmdb_details.release_date
            if not vote_average and tmdb_details.vote_average:
                vote_average = tmdb_details.vote_average
            if not cast and tmdb_details.cast:
                cast = [c.model_dump() for c in tmdb_details.cast]
        except Exception:
            logger.warning(
                "Falha ao buscar detalhes TMDB para %s; continuando sem enriquecer.",
                schema.external_tmdb_id,
            )

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
        genre=genre,
        age_rating=age_rating,
        director=director,
        release_date=release_date,
        vote_average=vote_average,
        cast=cast,
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
    genre: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Event], int]:
    """Lista eventos paginados com filtro opcional por titulo e genero.

    aplicando LIMIT/OFFSET diretamente na query do banco.

    Args:
        session: sessao async do banco.
        search: texto para filtro ILIKE no titulo (opcional).
        genre: filtro exato de genero (opcional).
        page: numero da pagina (1-indexado).
        page_size: quantidade de itens por pagina.

    Returns:
        Tupla (lista de eventos da pagina, total geral de eventos).
    """
    query = select(Event).where(
        Event.deleted_at.is_(None),
        Event.event_date >= aware_utcnow()
    )
    count_query = select(func.count()).select_from(Event).where(
        Event.deleted_at.is_(None),
        Event.event_date >= aware_utcnow()
    )

    if search and search.strip():
        pattern = f"%{search.strip()}%"
        query = query.where(Event.title.ilike(pattern))
        count_query = count_query.where(Event.title.ilike(pattern))

    if genre and genre.strip():
        # Match exato ou ilike, preferivel ilike para evitar problemas de case, mas como e dropdown exato ta otimo
        # O modelo Event tem genre como String, que pode conter multiplos generos separados por virgula.
        # Vamos usar ilike com %genre% para achar se a string contem a palavra.
        genre_pattern = f"%{genre.strip()}%"
        query = query.where(Event.genre.ilike(genre_pattern))
        count_query = count_query.where(Event.genre.ilike(genre_pattern))

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
    seats = list(result.scalars().all())

    # Mapeamento dinâmico: se está PENDING e já expirou (15 min),
    # exibe como AVAILABLE sem fazer DB write no endpoint GET.
    cutoff = aware_utcnow() - timedelta(minutes=15)
    for seat in seats:
        if seat.status == SeatStatus.PENDING and seat.updated_at and seat.updated_at < cutoff:
            # Retira o objeto da sessão para evitar que o SQLAlchemy
            # tente comitar essa mudança de "visualização" no banco.
            session.expunge(seat)
            seat.status = SeatStatus.AVAILABLE

    return seats


async def get_event_analytics(
    session: AsyncSession,
    organizer_id: UUID,
    event_id: UUID,
) -> EventAnalyticsResponseSchema:
    """Gera relatorio de ocupacao e faturamento de um evento.

    Blindagem IDOR: valida estritamente que o evento pertence ao
    organizer_id informado antes de retornar qualquer dado.

    Args:
        session: sessao async do banco.
        organizer_id: UUID do organizador autenticado.
        event_id: UUID do evento a ser consultado.

    Returns:
        EventAnalyticsResponseSchema com metricas de ocupacao.

    Raises:
        403: organizador nao e dono do evento.
        404: evento nao encontrado ou soft-deleted.
    """
    event = await get_event_by_id(session, event_id)

    if event.organizer_id != organizer_id:
        raise forbidden_error(
            "Voce nao tem permissao para visualizar os dados deste evento."
        )

    occupied_statuses = (SeatStatus.RESERVED, SeatStatus.PENDING)
    result = await session.execute(
        select(Seat.seat_number)
        .where(
            Seat.event_id == event_id,
            Seat.deleted_at.is_(None),
            Seat.status.in_(occupied_statuses),
        )
        .order_by(Seat.seat_number.asc())
    )
    occupied_seats = list(result.scalars().all())

    total_sold = len(occupied_seats)
    available_seats = event.capacity - total_sold
    revenue = Decimal(total_sold) * event.price

    return EventAnalyticsResponseSchema(
        event_id=event.id,
        title=event.title,
        capacity=event.capacity,
        total_sold=total_sold,
        available_seats=available_seats,
        revenue=revenue,
        occupied_seats=occupied_seats,
    )


async def list_organizer_events(
    session: AsyncSession,
    organizer_id: UUID,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Event], int]:
    """Lista eventos do organizador autenticado com paginacao.

    Args:
        session: sessao async do banco.
        organizer_id: UUID do organizador autenticado.
        page: numero da pagina (1-indexado).
        page_size: quantidade de itens por pagina.

    Returns:
        Tupla (lista de eventos da pagina, total geral).
    """
    base_filter = (
        Event.organizer_id == organizer_id,
        Event.deleted_at.is_(None),
    )

    query = (
        select(Event)
        .where(*base_filter)
        .order_by(Event.event_date.desc())
        .limit(page_size)
        .offset((page - 1) * page_size)
    )
    count_query = (
        select(func.count())
        .select_from(Event)
        .where(*base_filter)
    )

    result = await session.execute(query)
    events = list(result.scalars().all())

    count_result = await session.execute(count_query)
    total = count_result.scalar_one()

    return events, total


async def update_organizer_event(
    session: AsyncSession,
    organizer_id: UUID,
    event_id: UUID,
    schema: UpdateEventSchema,
) -> Event:
    """Atualiza campos de um evento existente (apenas o organizador dono).

    Args:
        session: sessao async do banco.
        organizer_id: UUID do organizador autenticado.
        event_id: UUID do evento a ser atualizado.
        schema: campos a atualizar (parciais).

    Returns:
        Event atualizado.

    Raises:
        400: nova data do evento esta no passado.
        403: organizador nao e dono do evento.
        404: evento nao encontrado ou soft-deleted.
    """
    event = await get_event_by_id(session, event_id)

    if event.organizer_id != organizer_id:
        raise forbidden_error(
            "Voce nao tem permissao para gerenciar este evento."
        )

    # Trava de integridade: checa se ha ingressos ativos
    active_ticket_count = await session.execute(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.event_id == event_id,
            Ticket.deleted_at.is_(None),
            Ticket.status != TicketStatus.CANCELLED,
        )
    )
    if active_ticket_count.scalar_one() > 0:
        raise conflict_error(
            "Nao e possivel alterar esta sessao pois ja existem "
            "ingressos vendidos para participantes."
        )

    update_data = schema.model_dump(exclude_unset=True)

    if "event_date" in update_data and update_data["event_date"] is not None:
        if ensure_aware_utc(update_data["event_date"]) < aware_utcnow():
            raise validation_error("A data e hora da sessao devem ser no futuro.")

    for field, value in update_data.items():
        setattr(event, field, value)

    # Sincroniza assentos se a capacidade mudou em evento SEATED
    if "capacity" in update_data and event.type == EventType.SEATED:
        new_capacity = update_data["capacity"]
        existing_seats_result = await session.execute(
            select(Seat)
            .where(Seat.event_id == event_id, Seat.deleted_at.is_(None))
            .order_by(Seat.seat_number.asc())
        )
        existing_seats = list(existing_seats_result.scalars().all())
        current_count = len(existing_seats)

        if new_capacity > current_count:
            # Adiciona assentos faltantes (A{current+1} ate A{new_capacity})
            new_seats = [
                Seat(
                    event_id=event_id,
                    seat_number=f"A{i}",
                    status=SeatStatus.AVAILABLE,
                )
                for i in range(current_count + 1, new_capacity + 1)
            ]
            session.add_all(new_seats)
        elif new_capacity < current_count:
            # Soft-delete de assentos excedentes que estejam AVAILABLE (do final)
            # para preservar integridade referencial e historico de auditoria.
            seats_to_remove = [
                s for s in existing_seats
                if s.status == SeatStatus.AVAILABLE
            ]
            # Ordena decrescente para remover do final
            seats_to_remove.sort(key=lambda s: s.seat_number, reverse=True)
            remove_count = current_count - new_capacity
            for seat in seats_to_remove[:remove_count]:
                seat.deleted_at = aware_utcnow()

    await session.commit()
    await session.refresh(event)
    return event


async def delete_organizer_event(
    session: AsyncSession,
    organizer_id: UUID,
    event_id: UUID,
) -> None:
    """Soft-delete de um evento com trava de integridade financeira.

    Impede exclusao se ja existem ingressos vendidos (nao-cancelados)
    vinculados ao evento, protegendo os participantes.

    Args:
        session: sessao async do banco.
        organizer_id: UUID do organizador autenticado.
        event_id: UUID do evento a ser excluido.

    Raises:
        403: organizador nao e dono do evento.
        404: evento nao encontrado ou soft-deleted.
        409: evento possui ingressos ativos vendidos.
    """
    event = await get_event_by_id(session, event_id)

    if event.organizer_id != organizer_id:
        raise forbidden_error(
            "Voce nao tem permissao para gerenciar este evento."
        )

    # Trava de integridade: checa se ha ingressos ativos
    active_ticket_count = await session.execute(
        select(func.count())
        .select_from(Ticket)
        .where(
            Ticket.event_id == event_id,
            Ticket.deleted_at.is_(None),
            Ticket.status != TicketStatus.CANCELLED,
        )
    )
    if active_ticket_count.scalar_one() > 0:
        raise conflict_error(
            "Nao e possivel excluir este evento pois ja existem "
            "ingressos vendidos para participantes."
        )

    event.deleted_at = aware_utcnow()
    await session.commit()

    logger.info(
        "Evento %s ('%s') soft-deleted pelo organizador %s",
        event_id,
        event.title,
        organizer_id,
    )


async def get_my_pending_seats(
    session: AsyncSession, event_id: UUID, user_id: UUID
) -> list[str]:
    """Retorna os numeros dos assentos PENDING do usuario logado para o evento.

    Args:
        session: sessao async do banco.
        event_id: UUID do evento.
        user_id: UUID do usuario autenticado (Client).

    Returns:
        Lista de strings com os numeros dos assentos.
    """
    result = await session.execute(
        select(Seat.seat_number)
        .where(
            Seat.event_id == event_id,
            Seat.user_id == user_id,
            Seat.status == SeatStatus.PENDING,
            Seat.deleted_at.is_(None),
        )
        .order_by(Seat.seat_number.asc())
    )
    return list(result.scalars().all())


async def cancel_my_pending_seats(
    session: AsyncSession, event_id: UUID, user_id: UUID, seat_numbers: list[str]
) -> int:
    """Cancela (libera) assentos PENDING que pertencem ao usuario logado.

    Utiliza with_for_update() para evitar race conditions com webhooks de
    pagamento atrasados do Stripe. Somente assentos do proprio usuario e que
    estejam como PENDING serao liberados (Protecao IDOR e de Estado).

    Args:
        session: sessao async do banco.
        event_id: UUID do evento.
        user_id: UUID do usuario autenticado (Client).
        seat_numbers: lista de assentos para cancelar.

    Returns:
        Numero de assentos efetivamente liberados.
    """
    if not seat_numbers:
        return 0

    # Bloqueio das linhas no banco antes de qualquer alteracao
    result = await session.execute(
        select(Seat)
        .where(
            Seat.event_id == event_id,
            Seat.user_id == user_id,
            Seat.seat_number.in_(seat_numbers),
            Seat.status == SeatStatus.PENDING,
            Seat.deleted_at.is_(None),
        )
        .with_for_update()
    )
    seats_to_release = list(result.scalars().all())

    if not seats_to_release:
        return 0

    # Atualiza o status para AVAILABLE e remove a propriedade
    for seat in seats_to_release:
        seat.status = SeatStatus.AVAILABLE
        seat.user_id = None

    await session.commit()
    logger.info(
        "Usuario %s cancelou manualmente %d assentos PENDING no evento %s",
        user_id,
        len(seats_to_release),
        event_id,
    )
    return len(seats_to_release)
