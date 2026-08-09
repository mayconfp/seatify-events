"""Schemas Pydantic v2 do modulo de eventos.

DTOs de entrada e resposta para CRUD de eventos, listagem de assentos
e busca no TMDb.
"""

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, Field

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
    type: EventType
    external_tmdb_id: str | None = None
    poster_url: str | None = None


class EventResponseSchema(BaseModel):
    """Representacao publica de um evento."""

    id: UUID
    organizer_id: UUID
    title: str
    description: str | None
    poster_url: str | None
    event_date: datetime
    venue_name: str
    capacity: int
    price: Decimal
    type: EventType
    external_tmdb_id: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


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


class TmdbMovieSchema(BaseModel):
    """Filme retornado pela API do TMDb."""

    id: int
    title: str
    overview: str | None = None
    poster_path: str | None = None
    release_date: str | None = None


class TmdbSearchResponseSchema(BaseModel):
    """Resposta da busca no TMDb."""

    results: list[TmdbMovieSchema]
    total_results: int
