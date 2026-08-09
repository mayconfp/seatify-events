"""Schemas Pydantic v2 do modulo de checkout.

DTOs para simulacao de pagamento e processamento de webhook.
"""

from uuid import UUID

from pydantic import BaseModel, Field


class SimulatePaymentSchema(BaseModel):
    """Payload para simulacao de pagamento."""

    event_id: UUID
    seat_numbers: list[str] = Field(..., min_length=1, max_length=10)
    simulate_failure: bool = False


class SimulatePaymentResponseSchema(BaseModel):
    """Resposta da simulacao de pagamento."""

    status: str
    stripe_event_id: str
    message: str


class WebhookPayloadSchema(BaseModel):
    """Payload simulado de webhook Stripe (payment_intent.succeeded).

    Usado exclusivamente pelo fluxo de simulacao interno (/checkout/simulate).
    O webhook real (/checkout/webhook) recebe o payload bruto do Stripe e
    verifica a assinatura criptografica.
    """

    stripe_event_id: str
    event_type: str = "payment_intent.succeeded"
    event_id: UUID
    client_id: UUID
    seat_numbers: list[str]


class CreateCheckoutSessionSchema(BaseModel):
    """Payload para criar uma Stripe Checkout Session real."""

    event_id: UUID
    seat_numbers: list[str] = Field(..., min_length=1, max_length=10)


class CreateCheckoutSessionResponseSchema(BaseModel):
    """Resposta da criacao de Checkout Session no Stripe."""

    session_id: str
    checkout_url: str
