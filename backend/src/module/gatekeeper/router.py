"""Rotas do modulo de portaria (gatekeeper).

Thin handler para validacao de ingressos na entrada do evento.
"""

from typing import Annotated

from fastapi import APIRouter, Depends, Request

from src.deps import SessionDep, limiter, require_role
from src.module.auth.model import User, UserRole
from src.module.gatekeeper import service
from src.module.gatekeeper.schemas import (
    ValidateEntrySchema,
    ValidationResultSchema,
)

router = APIRouter(prefix="/gatekeeper", tags=["Gatekeeper"])

GatekeeperDep = Annotated[User, Depends(require_role([UserRole.GATEKEEPER]))]


@router.post("/validate", response_model=ValidationResultSchema)
@limiter.limit("120/minute")
async def validate_entry(
    request: Request,
    schema: ValidateEntrySchema,
    session: SessionDep,
    _gatekeeper: GatekeeperDep,
) -> ValidationResultSchema:
    """Valida ingresso na portaria (apenas GATEKEEPER).

    Aceita QR Code token (JWT) ou share_link_hash (digitacao manual).
    Retorna um de 4 status: VALID, INVALID, ALREADY_USED, WRONG_EVENT.
    """
    return await service.validate_ticket_entry(
        session, schema.qr_token_or_hash, schema.event_id
    )
