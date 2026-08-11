"""Rotas do modulo de checkout.

Thin routers para criacao de Stripe Checkout Session, recepcao do
webhook real (com verificacao criptografica) e simulacao de pagamento
para desenvolvimento local sem ngrok.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Request

from src.deps import SessionDep, limiter, require_role
from src.module.auth.model import User, UserRole
from src.module.checkout import service
from src.module.checkout.schemas import (
    CreateCheckoutSessionResponseSchema,
    CreateCheckoutSessionSchema,
    SimulatePaymentResponseSchema,
    SimulatePaymentSchema,
)

router = APIRouter(prefix="/checkout", tags=["Checkout"])

ClientDep = Annotated[User, Depends(require_role([UserRole.CLIENT]))]


@router.post(
    "/create-session",
    response_model=CreateCheckoutSessionResponseSchema,
    status_code=201,
)
@limiter.limit("60/minute")
async def create_checkout_session(
    request: Request,
    schema: CreateCheckoutSessionSchema,
    session: SessionDep,
    client: ClientDep,
) -> CreateCheckoutSessionResponseSchema:
    """Cria uma Stripe Checkout Session para os assentos reservados (CLIENT).

    Retorna a URL hospedada do Stripe Checkout que o front-end deve abrir
    para o cliente concluir o pagamento com cartao.
    """
    return await service.create_stripe_checkout_session(session, client, schema)


@router.post("/simulate", response_model=SimulatePaymentResponseSchema)
@limiter.limit("60/minute")
async def simulate_payment(
    request: Request,
    schema: SimulatePaymentSchema,
    session: SessionDep,
    client: ClientDep,
) -> SimulatePaymentResponseSchema:
    """Simula pagamento de reserva (apenas CLIENT).

    Rota de fallback para desenvolvimento local sem ngrok. Reserva os
    assentos, gera um stripe_event_id mock e dispara o webhook internamente
    para confirmar os ingressos sem passar pela API real do Stripe.
    """
    return await service.process_payment_simulation(session, client, schema)


@router.post("/webhook", status_code=200)
async def receive_webhook(
    request: Request,
    session: SessionDep,
    stripe_signature: Annotated[str | None, Header(alias="Stripe-Signature")] = None,
) -> dict[str, str]:
    """Recebe o webhook real do Stripe (publico, sem rate limit).

    Valida a assinatura criptografica do payload contra o segredo
    `stripe_webhook_secret` e processa eventos `checkout.session.completed`
    e `payment_intent.succeeded`. Endpoint idempotente:
    stripe_event_id duplicado retorna 200 sem reprocessar.
    """
    payload_bytes = await request.body()
    await service.handle_stripe_webhook(session, payload_bytes, stripe_signature)
    return {"status": "processed"}
