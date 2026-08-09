"""Schemas Pydantic v2 do modulo de portaria (gatekeeper).

DTOs para validacao de entrada com QR Code ou hash manual.
"""

import enum
from uuid import UUID

from pydantic import BaseModel


class ValidationStatus(str, enum.Enum):
    """Status de validacao de ingresso na portaria."""

    VALID = "VALID"
    INVALID = "INVALID"
    ALREADY_USED = "ALREADY_USED"
    WRONG_EVENT = "WRONG_EVENT"


class ValidateEntrySchema(BaseModel):
    """Payload para validacao de entrada na portaria."""

    qr_token_or_hash: str
    event_id: UUID


class ValidationResultSchema(BaseModel):
    """Resultado da validacao de ingresso."""

    status: ValidationStatus
    message: str
    ticket_id: UUID | None = None
