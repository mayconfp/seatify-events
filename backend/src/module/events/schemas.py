"""Schemas Pydantic v2 do modulo de eventos.

DTOs de entrada e resposta para CRUD de eventos, listagem de assentos
e busca no TMDb.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator

from src.module.events.model import EventType
from src.module.tickets.model import SeatStatus


class CreateEventSchema(BaseModel):
    """Payload para criacao de evento."""

    title: str = Field(..., min_length=3, max_length=255)
    description: str | None = None
    event_date: datetime
    venue_name: str = Field(..., min_length=2, max_length=255)
    capacity: int = Field(..., gt=0, le=10000)
    price: Decimal = Field(..., ge=0, decimal_places=2)
    type: EventType = EventType.SEATED
    external_tmdb_id: str | None = None
    poster_url: str | None = None
    genre: str | None = None
    age_rating: str | None = None
    director: str | None = None
    release_date: str | None = None
    vote_average: float | None = None
    cast: list[dict] | None = None

    @field_validator("type")
    @classmethod
    def only_seated_allowed(cls, v: EventType) -> EventType:
        if v != EventType.SEATED:
            raise ValueError(
                "Apenas o tipo SEATED e suportado nesta versao da plataforma."
            )
        return v


class UpdateEventSchema(BaseModel):
    """Payload para atualizacao parcial de um evento existente."""

    title: str | None = Field(None, min_length=3, max_length=255)
    description: str | None = None
    event_date: datetime | None = None
    venue_name: str | None = Field(None, min_length=2, max_length=255)
    capacity: int | None = Field(None, gt=0, le=10000)
    price: Decimal | None = Field(None, ge=0, decimal_places=2)
    type: EventType | None = None
    external_tmdb_id: str | None = None
    poster_url: str | None = None
    genre: str | None = None
    age_rating: str | None = None
    director: str | None = None
    release_date: str | None = None
    vote_average: float | None = None
    cast: list[dict] | None = None

    @field_validator("type")
    @classmethod
    def only_seated_allowed(cls, v: EventType | None) -> EventType | None:
        if v is not None and v != EventType.SEATED:
            raise ValueError(
                "Apenas o tipo SEATED e suportado nesta versao da plataforma."
            )
        return v


class EventResponseSchema(BaseModel):
    """Representacao publica de um evento."""

    id: UUID
    title: str
    description: str | None
    poster_url: str | None
    event_date: datetime
    venue_name: str
    capacity: int
    price: Decimal
    type: EventType
    external_tmdb_id: str | None
    genre: str | None = None
    age_rating: str | None = None
    director: str | None = None
    release_date: str | None = None
    vote_average: float | None = None
    cast: list[dict] | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class EventAnalyticsResponseSchema(BaseModel):
    """Relatorio de ocupacao e faturamento de um evento para o organizador."""

    event_id: UUID
    title: str
    capacity: int
    total_sold: int
    available_seats: int
    revenue: Decimal
    occupied_seats: list[str]


class EventListResponseSchema(BaseModel):
    """Lista paginada de eventos."""

    events: list[EventResponseSchema]
    total: int
    page: int
    page_size: int


class SeatResponseSchema(BaseModel):
    """Representacao publica de um assento."""

    id: UUID
    seat_number: str
    status: SeatStatus

    model_config = {"from_attributes": True}


class TmdbCastMemberSchema(BaseModel):
    """Membro do elenco retornado pela API do TMDb."""

    name: str
    character: str | None = None
    profile_path: str | None = None


class TmdbMovieSchema(BaseModel):
    """Filme retornado pela API do TMDb."""

    id: int
    title: str
    overview: str | None = None
    poster_path: str | None = None
    release_date: str | None = None
    genres: list[str] = Field(default_factory=list)
    age_rating: str | None = None
    director: str | None = None
    vote_average: float | None = None
    popularity: float | None = None
    cast: list[TmdbCastMemberSchema] = Field(default_factory=list)


class TmdbSearchResponseSchema(BaseModel):
    """Resposta da busca no TMDb."""

    results: list[TmdbMovieSchema]
    total_results: int


class TmdbTrendingResponseSchema(BaseModel):
    """Resposta de filmes em alta do TMDb."""

    results: list[TmdbMovieSchema]
    time_window: str
