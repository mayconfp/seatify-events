"""Camada de negocio do modulo de checkout.

Responsabilidades: criacao de Stripe Checkout Sessions, processamento de
webhooks com verificacao criptografica de assinatura e idempotencia,
simulacao interna de pagamento (fallback sem ngrok) e emissao de ingressos.
"""

import asyncio
import json
import logging
import secrets
import uuid
from decimal import Decimal
from uuid import UUID

import stripe
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.errors.router import not_found_error, validation_error
from src.module.auth.model import User
from src.module.checkout.model import ProcessedWebhookEvent
from src.module.checkout.schemas import (
    CreateCheckoutSessionResponseSchema,
    CreateCheckoutSessionSchema,
    SimulatePaymentResponseSchema,
    SimulatePaymentSchema,
    WebhookPayloadSchema,
)
from src.module.events.model import Event
from src.module.tickets.model import Seat, SeatStatus, Ticket, TicketStatus
from src.util.datetime_utils import aware_utcnow
from src.util.jwt_utils import create_qr_token

logger = logging.getLogger("eventify.checkout.service")

# Inicializa a chave da API do Stripe uma unica vez no import do modulo.
stripe.api_key = settings.stripe_secret_key

_SUPPORTED_EVENT_TYPES = frozenset(
    {"checkout.session.completed", "payment_intent.succeeded", "charge.refunded"}
)


async def process_payment_simulation(
    session: AsyncSession,
    user: User,
    schema: SimulatePaymentSchema,
) -> SimulatePaymentResponseSchema:
    """Simula o fluxo de pagamento.

    1. Verifica se os assentos estao PENDING para o usuario.
    2. Gera um stripe_event_id mock.
    3. Se simulate_failure=True, reverte os assentos para AVAILABLE.

    Args:
        session: sessao async do banco.
        user: usuario CLIENT autenticado.
        schema: dados da simulacao.

    Returns:
        SimulatePaymentResponseSchema com status e stripe_event_id.
    """
    # Verifica se os assentos estao PENDING para este usuario
    result = await session.execute(
        select(Seat).where(
            Seat.event_id == schema.event_id,
            Seat.seat_number.in_(schema.seat_numbers),
            Seat.user_id == user.id,
            Seat.status == SeatStatus.PENDING,
            Seat.deleted_at.is_(None),
        )
    )
    reserved_seats = list(result.scalars().all())
    
    if len(reserved_seats) != len(schema.seat_numbers):
        raise validation_error("Os assentos informados nao estao reservados (PENDING) para este usuario.")

    # Gera stripe_event_id mock
    stripe_event_id = f"evt_sim_{uuid.uuid4().hex[:16]}"

    if schema.simulate_failure:
        # Falha simulada: reverte assentos para AVAILABLE
        for seat in reserved_seats:
            seat.status = SeatStatus.AVAILABLE
            seat.user_id = None
        await session.commit()
        return SimulatePaymentResponseSchema(
            status="failed",
            stripe_event_id=stripe_event_id,
            message="Pagamento simulado com falha. Assentos liberados.",
        )

    # Sucesso: dispara webhook internamente para confirmar
    webhook_payload = WebhookPayloadSchema(
        stripe_event_id=stripe_event_id,
        event_type="payment_intent.succeeded",
        event_id=schema.event_id,
        client_id=user.id,
        seat_numbers=schema.seat_numbers,
    )
    await _confirm_reservation_payment(
        session,
        stripe_event_id=webhook_payload.stripe_event_id,
        event_type=webhook_payload.event_type,
        event_id=webhook_payload.event_id,
        client_id=webhook_payload.client_id,
        seat_numbers=webhook_payload.seat_numbers,
        payment_intent_id=f"pi_sim_{uuid.uuid4().hex[:16]}",
    )

    return SimulatePaymentResponseSchema(
        status="succeeded",
        stripe_event_id=stripe_event_id,
        message="Pagamento simulado com sucesso. Ingressos emitidos.",
    )


async def _confirm_reservation_payment(
    session: AsyncSession,
    *,
    stripe_event_id: str,
    event_type: str,
    event_id: UUID,
    client_id: UUID,
    seat_numbers: list[str],
    payment_intent_id: str | None = None,
) -> int:
    """Confirma o pagamento de uma reserva com idempotencia.

    Nucleo compartilhado entre o webhook real do Stripe e a simulacao
    interna. Fluxo:
      1. Verifica idempotencia (fast-path por leitura previa).
      2. Trava e busca os assentos PENDING do cliente (SELECT FOR UPDATE).
      3. Converte PENDING -> RESERVED e emite tickets (QR token + share hash).
      4. Registra o evento processado; se o unique constraint disparar
         IntegrityError (duplicata concorrente), faz rollback e retorna 0.

    Returns:
        Numero de ingressos emitidos. Zero se o evento ja foi processado,
        se a reserva expirou ou se houve divergencia na contagem de assentos.
    """
    # 1. Verificacao de idempotencia (fast-path por leitura previa)
    existing = await session.execute(
        select(ProcessedWebhookEvent).where(
            ProcessedWebhookEvent.stripe_event_id == stripe_event_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.info("Webhook ja processado: %s", stripe_event_id)
        return 0

    # 2. Busca assentos PENDING do cliente com trava de linha
    result = await session.execute(
        select(Seat)
        .where(
            Seat.event_id == event_id,
            Seat.seat_number.in_(seat_numbers),
            Seat.user_id == client_id,
            Seat.status == SeatStatus.PENDING,
            Seat.deleted_at.is_(None),
        )
        .with_for_update()
    )
    seats = list(result.scalars().all())

    if not seats:
        logger.warning(
            "Pagamento recebido para reserva expirada ou inexistente (%s)",
            stripe_event_id,
        )
        session.add(
            ProcessedWebhookEvent(
                stripe_event_id=stripe_event_id,
                event_type=f"{event_type}:expired",
                processed_at=aware_utcnow(),
            )
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        return 0

    if len(seats) != len(seat_numbers):
        logger.error(
            "Divergencia na quantidade de assentos PENDING para o pagamento %s "
            "(esperado=%d, encontrado=%d)",
            stripe_event_id,
            len(seat_numbers),
            len(seats),
        )
        session.add(
            ProcessedWebhookEvent(
                stripe_event_id=stripe_event_id,
                event_type=f"{event_type}:seat_mismatch",
                processed_at=aware_utcnow(),
            )
        )
        try:
            await session.commit()
        except IntegrityError:
            await session.rollback()
        return 0

    # 3. Confirma assentos e emite ingressos
    for seat in seats:
        seat.status = SeatStatus.RESERVED

        ticket = Ticket(
            reservation_id=seat.id,
            client_id=client_id,
            event_id=event_id,
            seat_number=seat.seat_number,
            payment_intent_id=payment_intent_id,
            qr_code_token="",  # placeholder ate flush
            share_link_hash=secrets.token_urlsafe(16),
            status=TicketStatus.VALID,
        )
        session.add(ticket)
        await session.flush()

        # Gera QR token com ticket_id e event_id reais
        ticket.qr_code_token = create_qr_token(
            ticket_id=ticket.id,
            event_id=event_id,
        )

    # 4. Registra evento processado para idempotencia
    processed = ProcessedWebhookEvent(
        stripe_event_id=stripe_event_id,
        event_type=event_type,
        processed_at=aware_utcnow(),
    )
    session.add(processed)

    # 5. Commit protegido: dois webhooks duplicados simultaneos passam pela
    # leitura previa, mas o unique index em stripe_event_id impede a duplicata.
    try:
        await session.commit()
    except IntegrityError:
        await session.rollback()
        logger.info(
            "Webhook duplicado detectado no commit (idempotente): %s",
            stripe_event_id,
        )
        return 0

    logger.info(
        "Webhook processado: %s — %d ingressos emitidos",
        stripe_event_id,
        len(seats),
    )
    return len(seats)


async def handle_payment_webhook(
    session: AsyncSession,
    payload: WebhookPayloadSchema,
) -> None:
    """Adapter do webhook simulado (usado por /checkout/simulate).

    Encaminha para o nucleo compartilhado _confirm_reservation_payment.
    """
    await _confirm_reservation_payment(
        session,
        stripe_event_id=payload.stripe_event_id,
        event_type=payload.event_type,
        event_id=payload.event_id,
        client_id=payload.client_id,
        seat_numbers=payload.seat_numbers,
    )


async def create_stripe_checkout_session(
    session: AsyncSession,
    user: User,
    schema: CreateCheckoutSessionSchema,
) -> CreateCheckoutSessionResponseSchema:
    """Cria uma Stripe Checkout Session real para os assentos reservados.

    Fluxo:
      1. Valida que todos os assentos estao PENDING para o usuario logado.
      2. Carrega o evento (titulo/preco) para montar o line_item.
      3. Chama stripe.checkout.Session.create dentro de asyncio.to_thread
         para nao bloquear o event loop do FastAPI.
      4. Retorna a URL do Checkout e o session_id do Stripe.

    Raises:
        400: assentos nao estao PENDING para o usuario.
        404: evento nao encontrado.
        502: erro na API do Stripe.
    """
    # 1. Valida propriedade dos assentos
    result = await session.execute(
        select(Seat).where(
            Seat.event_id == schema.event_id,
            Seat.seat_number.in_(schema.seat_numbers),
            Seat.user_id == user.id,
            Seat.status == SeatStatus.PENDING,
            Seat.deleted_at.is_(None),
        )
    )
    reserved_seats = list(result.scalars().all())
    if len(reserved_seats) != len(schema.seat_numbers):
        raise validation_error(
            "Os assentos informados nao estao reservados (PENDING) para este usuario."
        )

    # 2. Carrega o evento para obter titulo e preco
    event = await session.get(Event, schema.event_id)
    if event is None or event.deleted_at is not None:
        raise not_found_error("Evento nao encontrado")

    # Preco em centavos (menor unidade monetaria — regra do Stripe).
    unit_amount = int((event.price * Decimal(100)).to_integral_value())

    metadata = {
        "event_id": str(schema.event_id),
        "client_id": str(user.id),
        "seat_numbers": json.dumps(schema.seat_numbers),
    }

    # 3. Chamada sincrona da SDK Stripe dentro de asyncio.to_thread
    try:
        stripe_session = await asyncio.to_thread(
            stripe.checkout.Session.create,
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "price_data": {
                        "currency": "brl",
                        "unit_amount": unit_amount,
                        "product_data": {
                            "name": event.title,
                            "description": (
                                f"Assentos: {', '.join(schema.seat_numbers)}"
                            ),
                        },
                    },
                    "quantity": len(schema.seat_numbers),
                }
            ],
            success_url=(
                f"{settings.frontend_url}/checkout/success"
                "?session_id={CHECKOUT_SESSION_ID}"
            ),
            cancel_url=f"{settings.frontend_url}/checkout/cancel",
            metadata=metadata,
            payment_intent_data={"metadata": metadata},
        )
    except stripe.error.StripeError as exc:
        logger.warning("Falha na criacao da Stripe Checkout Session: %s", exc)
        raise validation_error(f"Falha ao criar sessao do Stripe: {exc}") from exc

    logger.info(
        "Stripe Checkout Session criada: %s (event=%s, seats=%s)",
        stripe_session.id,
        schema.event_id,
        schema.seat_numbers,
    )
    return CreateCheckoutSessionResponseSchema(
        session_id=stripe_session.id,
        checkout_url=stripe_session.url,
    )


def _extract_metadata(event: stripe.Event) -> tuple[UUID, UUID, list[str], str | None]:
    """Extrai (event_id, client_id, seat_numbers, payment_intent_id) dos metadados do evento Stripe.

    Suporta payloads de checkout.session.completed (Session) e
    payment_intent.succeeded (PaymentIntent). Ambos carregam metadata dict.

    Raises:
        400: metadados ausentes ou malformados.
    """
    data_object = event.get("data", {}).get("object") or {}
    metadata = data_object.get("metadata") or {}
    
    payment_intent_id = None
    if event.get("type") == "checkout.session.completed":
        payment_intent_id = data_object.get("payment_intent")
    elif event.get("type") == "payment_intent.succeeded":
        payment_intent_id = data_object.get("id")
        
    try:
        event_id = UUID(metadata["event_id"])
        client_id = UUID(metadata["client_id"])
        seat_numbers_raw = metadata["seat_numbers"]
    except (KeyError, TypeError, ValueError) as exc:
        raise validation_error(
            "Metadados do evento Stripe ausentes ou invalidos."
        ) from exc

    try:
        seat_numbers = json.loads(seat_numbers_raw)
    except (TypeError, json.JSONDecodeError) as exc:
        raise validation_error(
            "Campo 'seat_numbers' do metadata nao esta em formato JSON valido."
        ) from exc

    if not isinstance(seat_numbers, list) or not all(
        isinstance(s, str) for s in seat_numbers
    ):
        raise validation_error(
            "Campo 'seat_numbers' do metadata deve ser uma lista de strings."
        )

    return event_id, client_id, seat_numbers, payment_intent_id


async def handle_stripe_webhook(
    session: AsyncSession,
    payload_bytes: bytes,
    sig_header: str | None,
) -> None:
    """Processa webhook real do Stripe com verificacao criptografica.

    1. Verifica a assinatura via stripe.Webhook.construct_event usando o
       segredo `settings.stripe_webhook_secret`. Assinatura invalida => 400.
    2. Ignora tipos de evento fora do escopo (retorna sem erro para o Stripe
       nao reenviar indefinidamente).
    3. Extrai metadados (event_id, client_id, seat_numbers) e delega para
       _confirm_reservation_payment (idempotente).

    Args:
        session: sessao async do banco.
        payload_bytes: corpo bruto da requisicao HTTP.
        sig_header: cabecalho Stripe-Signature.

    Raises:
        400: assinatura invalida ou metadados malformados.
        500: stripe_webhook_secret nao configurado.
    """
    if not settings.stripe_webhook_secret:
        logger.error("stripe_webhook_secret nao configurado no ambiente.")
        raise validation_error(
            "Servidor sem segredo do webhook Stripe configurado."
        )

    if not sig_header:
        raise validation_error("Cabecalho 'Stripe-Signature' ausente.")

    try:
        stripe_event = stripe.Webhook.construct_event(
            payload=payload_bytes,
            sig_header=sig_header,
            secret=settings.stripe_webhook_secret,
        )
    except stripe.error.SignatureVerificationError as exc:
        logger.warning("Assinatura de webhook Stripe invalida: %s", exc)
        raise validation_error("Assinatura de Webhook invalida") from exc
    except ValueError as exc:
        logger.warning("Payload de webhook Stripe malformado: %s", exc)
        raise validation_error("Payload de Webhook invalido") from exc

    event_type = stripe_event.get("type", "")
    stripe_event_id = stripe_event.get("id", "")

    if event_type not in _SUPPORTED_EVENT_TYPES:
        logger.info(
            "Evento Stripe ignorado (tipo nao tratado): %s (%s)",
            event_type,
            stripe_event_id,
        )
        return

    if event_type == "charge.refunded":
        await _process_refund_webhook(session, stripe_event_id, stripe_event)
        return

    event_id, client_id, seat_numbers, payment_intent_id = _extract_metadata(stripe_event)

    await _confirm_reservation_payment(
        session,
        stripe_event_id=stripe_event_id,
        event_type=event_type,
        event_id=event_id,
        client_id=client_id,
        seat_numbers=seat_numbers,
        payment_intent_id=payment_intent_id,
    )


async def _process_refund_webhook(
    session: AsyncSession,
    stripe_event_id: str,
    event: stripe.Event,
) -> None:
    """Processa o estorno (refund) escutando o webhook do Stripe.
    
    Garante idempotencia, bloqueia os tickets, marca como CANCELLED,
    e devolve as cadeiras (Seat) para o status AVAILABLE.
    """
    data_object = event.get("data", {}).get("object") or {}
    payment_intent_id = data_object.get("payment_intent")
    
    if not payment_intent_id:
        return
        
    # Idempotencia
    existing = await session.execute(
        select(ProcessedWebhookEvent).where(
            ProcessedWebhookEvent.stripe_event_id == stripe_event_id
        )
    )
    if existing.scalar_one_or_none() is not None:
        logger.info("Refund webhook ja processado: %s", stripe_event_id)
        return

    # Trava tickets com esse pagamento
    result = await session.execute(
        select(Ticket)
        .where(Ticket.payment_intent_id == payment_intent_id, Ticket.status == TicketStatus.VALID)
        .with_for_update()
    )
    tickets = list(result.scalars().all())
    
    if not tickets:
        logger.info("Nenhum ticket valido encontrado para refund: %s", payment_intent_id)
        
    for ticket in tickets:
        ticket.status = TicketStatus.CANCELLED
        
        # Libera a cadeira
        seat_result = await session.execute(
            select(Seat).where(Seat.id == ticket.reservation_id).with_for_update()
        )
        seat = seat_result.scalar_one_or_none()
        if seat:
            seat.status = SeatStatus.AVAILABLE
            seat.user_id = None
            
    # Salva idempotencia
    processed = ProcessedWebhookEvent(
        stripe_event_id=stripe_event_id,
        event_type="charge.refunded",
        processed_at=aware_utcnow(),
    )
    session.add(processed)
    
    try:
        await session.commit()
        logger.info("Refund processado para %d ingressos (Payment %s)", len(tickets), payment_intent_id)
    except IntegrityError:
        await session.rollback()
        logger.info("Refund duplicado detectado: %s", stripe_event_id)
