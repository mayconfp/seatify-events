"""Rotas do modulo de ingressos.

Thin routers para reserva de assentos, listagem de ingressos
e acesso publico por share hash.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Request

from src.deps import SessionDep, limiter, require_role
from src.module.auth.model import User, UserRole
from src.module.tickets import service
from src.module.tickets.schemas import (
    ReservationResponseSchema,
    ReserveSeatsSchema,
    TicketResponseSchema,
)

router = APIRouter(tags=["Tickets"])

ClientDep = Annotated[User, Depends(require_role([UserRole.CLIENT]))]


@router.post(
    "/events/{event_id}/reserve",
    response_model=ReservationResponseSchema,
    status_code=201,
)
@limiter.limit("60/minute")
async def reserve_seats(
    request: Request,
    event_id: UUID,
    schema: ReserveSeatsSchema,
    session: SessionDep,
    client: ClientDep,
) -> ReservationResponseSchema:
    """Reserva assentos em um evento (apenas CLIENT).

    Os assentos ficam em status PENDING ate confirmacao via checkout.
    Assentos PENDING ha mais de 15 minutos sao automaticamente liberados.
    """
    seats = await service.reserve_seats(session, client, event_id, schema.seat_numbers)
    return ReservationResponseSchema(
        event_id=event_id,
        reserved_seats=[s.seat_number for s in seats],
        message=f"{len(seats)} assento(s) reservado(s) com sucesso. Finalize o checkout em ate 15 minutos.",
    )


@router.get("/tickets/me", response_model=list[TicketResponseSchema])
async def get_my_tickets(
    session: SessionDep,
    client: ClientDep,
) -> list[TicketResponseSchema]:
    """Retorna ingressos do usuario autenticado (apenas CLIENT)."""
    tickets = await service.get_user_tickets(session, client.id)
    return [TicketResponseSchema.model_validate(t) for t in tickets]


@router.get("/tickets/share/{share_link_hash}", response_model=TicketResponseSchema)
async def get_ticket_by_share(
    share_link_hash: str,
    session: SessionDep,
) -> TicketResponseSchema:
    """Retorna detalhes de um ingresso via link de compartilhamento (publico)."""
    ticket = await service.get_ticket_by_share_hash(session, share_link_hash)
    return TicketResponseSchema.model_validate(ticket)


@router.post(
    "/tickets/{ticket_id}/refund",
    status_code=202,
)
@limiter.limit("5/minute")
async def request_refund(
    request: Request,
    ticket_id: UUID,
    session: SessionDep,
    client: ClientDep,
) -> dict[str, str]:
    """Solicita reembolso de um ingresso (Apenas CLIENT).
    
    Usa a integracao assincrona (Opcao B - 2 horas) com o webhook do Stripe.
    """
    await service.request_refund(session, ticket_id, client.id)
    return {"message": "Solicitacao de reembolso enviada com sucesso ao provedor de pagamentos."}
