"""Camada de negocio do modulo de ingressos.

Responsabilidades: reserva de assentos com trava contra double-booking
(SELECT FOR UPDATE), listagem de tickets e busca por share hash.
Assentos PENDING ha mais de 15 minutos sao automaticamente liberados.
"""

import logging
from datetime import timedelta
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.errors.router import conflict_error, not_found_error, validation_error, forbidden_error
from src.module.auth.model import User
from src.module.events.service import get_event_by_id
from src.module.tickets.model import Seat, SeatStatus, Ticket, TicketStatus
from src.util.datetime_utils import aware_utcnow
import stripe
import asyncio

stripe.api_key = settings.stripe_secret_key

logger = logging.getLogger("eventify.tickets.service")

PENDING_EXPIRATION_MINUTES = 15
MAX_PENDING_SEATS_PER_USER = 10


async def _release_expired_pending_seats(
    session: AsyncSession,
    event_id: UUID,
) -> int:
    """Libera assentos PENDING ha mais de 15 minutos.

    Chamada antes de reservas e consultas de assentos para manter
    o mapa atualizado sem depender de job em background.

    Args:
        session: sessao async do banco.
        event_id: UUID do evento.

    Returns:
        Numero de assentos liberados.
    """
    cutoff = aware_utcnow() - timedelta(minutes=PENDING_EXPIRATION_MINUTES)
    result = await session.execute(
        update(Seat)
        .where(
            Seat.event_id == event_id,
            Seat.status == SeatStatus.PENDING,
            Seat.updated_at < cutoff,
        )
        .values(status=SeatStatus.AVAILABLE, user_id=None)
    )
    if result.rowcount > 0:
        logger.info(
            "Liberados %d assentos PENDING expirados do evento %s",
            result.rowcount,
            event_id,
        )
    return result.rowcount


async def reserve_seats(
    session: AsyncSession,
    user: User,
    event_id: UUID,
    seat_numbers: list[str],
) -> list[Seat]:
    """Reserva assentos com trava SELECT FOR UPDATE contra double-booking.

    1. Libera assentos PENDING expirados (> 15 min).
    2. Busca os assentos solicitados com FOR UPDATE (trava de linha).
    3. Valida que todos estao AVAILABLE.
    4. Atualiza para PENDING com user_id do cliente.

    Args:
        session: sessao async do banco.
        user: usuario CLIENT autenticado.
        event_id: UUID do evento.
        seat_numbers: lista de numeros de assento (ex: ["A1", "A2"]).

    Returns:
        Lista de Seat atualizados para PENDING.

    Raises:
        404: evento nao encontrado.
        400: assento solicitado nao existe.
        409: assento nao esta AVAILABLE (ja reservado ou pendente).
    """
    # Valida que o evento existe
    await get_event_by_id(session, event_id)

    # Libera PENDING expirados antes de tentar reservar
    await _release_expired_pending_seats(session, event_id)

    # Trava anti-hoarding: limita total de assentos PENDING por usuario POR EVENTO
    pending_count_result = await session.execute(
        select(func.count())
        .select_from(Seat)
        .where(
            Seat.event_id == event_id,
            Seat.user_id == user.id,
            Seat.status == SeatStatus.PENDING,
            Seat.deleted_at.is_(None),
        )
    )
    current_pending = pending_count_result.scalar_one()
    if current_pending + len(seat_numbers) > MAX_PENDING_SEATS_PER_USER:
        raise validation_error(
            f"Limite de {MAX_PENDING_SEATS_PER_USER} assentos pendentes por evento excedido. "
            f"Voce ja possui {current_pending} assento(s) pendente(s) neste evento."
        )

    # SELECT FOR UPDATE — trava as linhas contra acesso concorrente.
    # order_by garante retorno deterministico (independente da ordem fisica
    # dos tuplos no heap do Postgres apos updates repetidos), alinhado com
    # a ordem publicada em get_event_seats.
    result = await session.execute(
        select(Seat)
        .where(
            Seat.event_id == event_id,
            Seat.seat_number.in_(seat_numbers),
            Seat.deleted_at.is_(None),
        )
        .order_by(Seat.seat_number.asc())
        .with_for_update()
    )
    found_seats = list(result.scalars().all())

    # Verifica se todos os assentos solicitados existem
    found_numbers = {s.seat_number for s in found_seats}
    missing = set(seat_numbers) - found_numbers
    if missing:
        raise validation_error(
            f"Assentos nao encontrados para este evento: {', '.join(sorted(missing))}"
        )

    # Verifica se todos estao AVAILABLE
    unavailable = [s for s in found_seats if s.status != SeatStatus.AVAILABLE]
    if unavailable:
        unavailable_numbers = [s.seat_number for s in unavailable]
        raise conflict_error(
            f"Assentos indisponiveis (ja reservados ou pendentes): {', '.join(unavailable_numbers)}"
        )

    # Atualiza para PENDING
    for seat in found_seats:
        seat.status = SeatStatus.PENDING
        seat.user_id = user.id

    await session.commit()

    # Refresh para garantir dados atualizados
    for seat in found_seats:
        await session.refresh(seat)

    return found_seats


async def get_user_tickets(session: AsyncSession, user_id: UUID) -> list[Ticket]:
    """Retorna todos os tickets do usuario.

    Args:
        session: sessao async do banco.
        user_id: UUID do usuario logado.

    Returns:
        Lista de Ticket do usuario.
    """
    result = await session.execute(
        select(Ticket)
        .options(joinedload(Ticket.event))
        .where(Ticket.client_id == user_id, Ticket.deleted_at.is_(None))
        .order_by(Ticket.created_at.desc())
    )
    return list(result.scalars().all())


async def get_ticket_by_share_hash(session: AsyncSession, share_link_hash: str) -> Ticket:
    """Busca um ticket pelo hash de compartilhamento (publico).

    Args:
        session: sessao async do banco.
        share_link_hash: hash unico do link de compartilhamento.

    Returns:
        Ticket encontrado.

    Raises:
        404: ticket nao encontrado.
    """
    result = await session.execute(
        select(Ticket)
        .options(joinedload(Ticket.event))
        .where(
            Ticket.share_link_hash == share_link_hash,
            Ticket.deleted_at.is_(None),
        )
    )
    ticket = result.scalar_one_or_none()
    if ticket is None:
        raise not_found_error("Ingresso nao encontrado")
    return ticket


async def request_refund(session: AsyncSession, ticket_id: UUID, user_id: UUID) -> None:
    """Solicita reembolso (Opcao B - 2 horas antes) chamando apenas a API do Stripe.
    
    A devolucao efetiva das cadeiras sera feita pelo webhook `charge.refunded`.
    """
    result = await session.execute(
        select(Ticket)
        .options(joinedload(Ticket.event))
        .where(Ticket.id == ticket_id, Ticket.deleted_at.is_(None))
    )
    ticket = result.scalar_one_or_none()
    
    if ticket is None:
        raise not_found_error("Ingresso nao encontrado")
        
    if ticket.client_id != user_id:
        raise forbidden_error("Este ingresso nao pertence a voce.")
        
    if ticket.status != TicketStatus.VALID:
        status_map = {
            "CANCELLED": "Cancelado",
            "USED": "Utilizado",
            "PENDING": "Pendente",
        }
        pt_status = status_map.get(ticket.status.value, ticket.status.value)
        raise validation_error(f"Ingresso nao pode ser reembolsado. Status atual: {pt_status}")
        
    if not ticket.payment_intent_id:
        raise validation_error("Nao eh possivel estornar um ingresso sem ID de transacao.")
        
    # Regra de 2 horas (CDC vs Eventos - Opcao B)
    now = aware_utcnow()
    event_start = ticket.event.event_date
    if event_start <= now + timedelta(hours=2):
        raise validation_error(
            "Cancelamento nao permitido. O evento comecara em menos de 2 horas "
            "ou ja ocorreu (Regra da plataforma)."
        )
        
    # Pagamentos simulados não suportam estorno automático na nossa regra de negócio
    if ticket.payment_intent_id and ticket.payment_intent_id.startswith("pi_sim_"):
        raise validation_error(
            "Pagamentos simulados (Modo Dev) não suportam reembolso. "
            "Apenas pagamentos reais via Stripe podem ser estornados."
        )

    # Chama Stripe
    
    try:
        await asyncio.to_thread(
            stripe.Refund.create,
            payment_intent=ticket.payment_intent_id,
        )
    except stripe.error.StripeError as exc:
        logger.error("Erro no reembolso Stripe (ticket_id=%s): %s", ticket_id, exc)
        raise validation_error(f"Falha ao processar estorno no provedor de pagamento: {exc}")


