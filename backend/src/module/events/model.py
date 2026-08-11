"""Modelo ORM do módulo de eventos.

Define o tipo de evento (SEATED com numeração de assentos vs PISTA sem
numeração) e a entidade Event com todos os metadados necessários para
exibição, filtragem e integração com o TMDB.
"""

import enum
import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import BaseModel, varchar_enum


class EventType(str, enum.Enum):
    # Modalidade de ingresso do evento.


    SEATED = "SEATED"
    PISTA = "PISTA"


class Event(BaseModel):
    """Evento publicado na plataforma.

    organizer_id é FK para users.id (papel ORGANIZER).
    external_tmdb_id permite enriquecer os dados via API do TMDB.
    price usa Numeric(10, 2) para precisão monetária sem ponto flutuante.
    """

    __tablename__ = "events"

    organizer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    external_tmdb_id: Mapped[str | None] = mapped_column(String(50), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    event_date: Mapped[datetime] = mapped_column(nullable=False)
    venue_name: Mapped[str] = mapped_column(String(255), nullable=False)
    capacity: Mapped[int] = mapped_column(Integer, nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    type: Mapped[EventType] = mapped_column(
        varchar_enum(EventType, name="event_type"),
        nullable=False,
    )
    genre: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    age_rating: Mapped[str | None] = mapped_column(String(50), nullable=True)
    director: Mapped[str | None] = mapped_column(String(255), nullable=True)
    release_date: Mapped[str | None] = mapped_column(String(50), nullable=True)
    vote_average: Mapped[Decimal | None] = mapped_column(Numeric(3, 1), nullable=True)
    cast: Mapped[list[dict] | None] = mapped_column(JSONB, nullable=True)

    # Relacionamentos (carregados explicitamente nas queries que precisarem)
    organizer = relationship("User", foreign_keys=[organizer_id], lazy="noload")
    seats = relationship("Seat", back_populates="event", lazy="noload")
