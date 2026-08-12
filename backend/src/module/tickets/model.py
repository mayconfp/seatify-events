"""Modelos ORM do módulo de ingressos.

Dois conceitos distintos:
- Seat: representa um assento físico (ou slot de PISTA) de um evento.
  Controla disponibilidade com lock (with_for_update()) para
  evitar double-booking em alta concorrência.
- Ticket: ingresso confirmado após pagamento. Contém o qr_code_token
  (JWT assinado, nunca ID bruto) e o share_link_hash para link de
  compartilhamento.
"""

import enum
import uuid

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.db.base import BaseModel, varchar_enum


class SeatStatus(str, enum.Enum):
    """Estado de disponibilidade de um assento/slot.

    - AVAILABLE: livre para reserva.
    - PENDING: em processo de checkout (reserva temporária).
    - RESERVED: confirmado por pagamento.
    """

    AVAILABLE = "AVAILABLE"
    PENDING = "PENDING"
    RESERVED = "RESERVED"


class TicketStatus(str, enum.Enum):
    """Estado de validade de um ingresso emitido.

    - VALID: pronto para uso na portaria.
    - USED: já utilizado — não pode ser revalidado.
    - CANCELLED: cancelado (reembolso ou estorno).
    """

    VALID = "VALID"
    USED = "USED"
    CANCELLED = "CANCELLED"


class Seat(BaseModel):
    """Assento ou slot de um evento.

    seat_number identifica o assento (ex.: "A1", "B3") para eventos SEATED
    ou um identificador sequencial para PISTA. A constraint de unicidade
    garante que não existam dois assentos com o mesmo número no mesmo evento.

    Transações de reserva devem usar SELECT ... FOR UPDATE (with_for_update)
    nesta tabela para evitar concorrência e double-booking.
    """

    __tablename__ = "seats"

    __table_args__ = (
        UniqueConstraint("event_id", "seat_number", name="uq_seats_event_id_seat_number"),
    )

    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    seat_number: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    status: Mapped[SeatStatus] = mapped_column(
        varchar_enum(SeatStatus, name="seat_status"),
        nullable=False,
        default=SeatStatus.AVAILABLE,
    )

    # Relacionamentos
    event = relationship("Event", back_populates="seats", lazy="noload")
    user = relationship("User", foreign_keys=[user_id], lazy="noload")
    ticket = relationship("Ticket", back_populates="seat", uselist=False, lazy="noload")


class Ticket(BaseModel):
    """Ingresso confirmado após pagamento bem-sucedido.

    qr_code_token: JWT assinado contendo ticket_id e event_id.
      Nunca contém dados brutos navegáveis. Validado pela portaria.
    share_link_hash: hash único para link de compartilhamento do ingresso.
    status: ciclo de vida do ingresso (VALID → USED ou CANCELLED).
    """

    __tablename__ = "tickets"

    reservation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("seats.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    client_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("events.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    seat_number: Mapped[str] = mapped_column(String(20), nullable=False)
    payment_intent_id: Mapped[str | None] = mapped_column(String(255), nullable=True, index=True)
    qr_code_token: Mapped[str] = mapped_column(String(2048), nullable=False)
    share_link_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    status: Mapped[TicketStatus] = mapped_column(
        varchar_enum(TicketStatus, name="ticket_status"),
        nullable=False,
        default=TicketStatus.VALID,
    )

    # Relacionamentos
    seat = relationship("Seat", back_populates="ticket", lazy="noload")
    client = relationship("User", foreign_keys=[client_id], lazy="noload")
    event = relationship("Event", foreign_keys=[event_id], lazy="noload")
