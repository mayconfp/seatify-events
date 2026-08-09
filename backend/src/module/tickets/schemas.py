"""Schemas Pydantic v2 do modulo de ingressos.

DTOs para reserva de assentos, listagem de tickets e compartilhamento.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from src.module.tickets.model import SeatStatus, TicketStatus


class ReserveSeatsSchema(BaseModel):
    """Payload para reserva de assentos em um evento."""

    seat_numbers: list[str] = Field(..., min_length=1, max_length=10)


class TicketResponseSchema(BaseModel):
    """Representacao publica de um ingresso emitido."""

    id: UUID
    event_id: UUID
    seat_number: str
    qr_code_token: str
    share_link_hash: str
    status: TicketStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class ReservationResponseSchema(BaseModel):
    """Resposta apos reserva de assentos (status PENDING)."""

    event_id: UUID
    reserved_seats: list[str]
    message: str


class SeatStatusSchema(BaseModel):
    """Status individual de um assento."""

    seat_number: str
    status: SeatStatus

    model_config = {"from_attributes": True}
