"""Modelo ORM do módulo de checkout.

ProcessedWebhookEvent garante idempotência no processamento de webhooks
do Stripe: antes de processar um evento, o router verifica se o
stripe_event_id já está na tabela. Se sim, retorna 200 sem reprocessar.
"""

from datetime import datetime

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from src.db.base import BaseModel
from src.util.datetime_utils import aware_utcnow


class ProcessedWebhookEvent(BaseModel):
    """Registro de eventos Stripe já processados.

    Garante idempotência: um mesmo stripe_event_id nunca é processado
    duas vezes, mesmo que o Stripe o reenvie por timeout ou falha.
    """

    __tablename__ = "processed_webhook_events"

    stripe_event_id: Mapped[str] = mapped_column(
        String(255), nullable=False, unique=True, index=True
    )
    event_type: Mapped[str] = mapped_column(String(100), nullable=False)
    processed_at: Mapped[datetime] = mapped_column(
        nullable=False, default=aware_utcnow
    )
