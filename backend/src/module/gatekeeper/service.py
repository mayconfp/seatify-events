"""Camada de negocio do modulo de portaria (gatekeeper).

Responsabilidade unica: validar ingresso na entrada do evento.
Suporta entrada via QR Code token (JWT) ou digitacao manual do
share_link_hash como fallback.

Retornos visiveis ao porteiro:
  - VALID: Acesso liberado.
  - INVALID: QR Code ou codigo invalido.
  - ALREADY_USED: Ingresso ja utilizado anteriormente.
  - WRONG_EVENT: Ingresso pertencente a outro evento.
"""

import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import joinedload
from sqlalchemy.ext.asyncio import AsyncSession

from src.module.gatekeeper.schemas import ValidationResultSchema, ValidationStatus
from src.module.tickets.model import Ticket, TicketStatus
from src.util.datetime_utils import aware_utcnow
from src.util.jwt_utils import decode_qr_token
from datetime import timedelta

logger = logging.getLogger("eventify.gatekeeper.service")


async def validate_ticket_entry(
    session: AsyncSession,
    qr_token_or_hash: str,
    event_id: UUID,
) -> ValidationResultSchema:
    """Valida um ingresso para entrada no evento.

    Fluxo:
    1. Tenta decodificar como QR token JWT.
    2. Se falhar, busca pelo share_link_hash (digitacao manual).
    3. Aplica regras de validacao: evento correto, status VALID.
    4. Se valido, marca como USED e persiste.

    Args:
        session: sessao async do banco.
        qr_token_or_hash: token JWT do QR Code ou share_link_hash.
        event_id: UUID do evento da portaria.

    Returns:
        ValidationResultSchema com status e mensagem.
    """
    ticket: Ticket | None = None

    # 1. Tenta decodificar como QR token JWT
    try:
        payload = decode_qr_token(qr_token_or_hash)
        ticket_id = UUID(payload["ticket_id"])

        result = await session.execute(
            select(Ticket)
            .options(joinedload(Ticket.event))
            .where(
                Ticket.id == ticket_id,
                Ticket.deleted_at.is_(None),
            )
            .with_for_update()
        )
        ticket = result.scalar_one_or_none()
    except (ValueError, KeyError):
        # Nao e um QR token valido — tenta como share_link_hash
        pass

    # 2. Fallback: busca por share_link_hash
    if ticket is None:
        result = await session.execute(
            select(Ticket)
            .options(joinedload(Ticket.event))
            .where(
                Ticket.share_link_hash == qr_token_or_hash,
                Ticket.deleted_at.is_(None),
            )
            .with_for_update()
        )
        ticket = result.scalar_one_or_none()

    # 3. Se nenhum ticket encontrado -> INVALID
    if ticket is None:
        return ValidationResultSchema(
            status=ValidationStatus.INVALID,
            message="QR Code ou codigo invalido",
        )

    # 4. Verifica se o ticket pertence ao evento correto
    if ticket.event_id != event_id:
        return ValidationResultSchema(
            status=ValidationStatus.WRONG_EVENT,
            message="Ingresso pertencente a outro evento",
            ticket_id=ticket.id,
        )

    # 5. Verifica a Janela de Tempo (Time Window)
    # Entrada permitida de 2 horas antes ate 4 horas depois do inicio
    now = aware_utcnow()
    event_time = ticket.event.event_date
    window_start = event_time - timedelta(hours=2)
    window_end = event_time + timedelta(hours=4)

    if not (window_start <= now <= window_end):
        return ValidationResultSchema(
            status=ValidationStatus.WRONG_TIME,
            message="Ingresso fora do horario permitido da sessao",
            ticket_id=ticket.id,
        )

    # 5. Verifica se o ticket ja foi utilizado
    if ticket.status == TicketStatus.USED:
        return ValidationResultSchema(
            status=ValidationStatus.ALREADY_USED,
            message="Ingresso ja utilizado anteriormente",
            ticket_id=ticket.id,
        )

    # 6. Verifica se o ticket foi cancelado
    if ticket.status == TicketStatus.CANCELLED:
        return ValidationResultSchema(
            status=ValidationStatus.INVALID,
            message="Ingresso cancelado",
            ticket_id=ticket.id,
        )

    # 7. Ticket VALID -> marca como USED
    ticket.status = TicketStatus.USED
    await session.commit()

    logger.info("Ingresso %s validado para evento %s", ticket.id, event_id)

    return ValidationResultSchema(
        status=ValidationStatus.VALID,
        message="Acesso liberado",
        ticket_id=ticket.id,
    )
