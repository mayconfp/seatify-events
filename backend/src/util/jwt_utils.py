"""Utilitários JWT para autenticação e tokens de QR Code.

Dois tipos de token são emitidos:
- **Access token**: autenticação de usuário (Bearer), contém `sub` = user_id e `role`.
- **QR token**: token infalsificável embutido no QR Code do ingresso, contém
  `ticket_id` e `event_id`. Nunca expõe o ID numérico bruto.

Ambos são assinados com `JWT_SECRET_KEY` + `JWT_ALGORITHM` (HS256).
"""

import uuid
from datetime import timedelta
from typing import Any

import jwt

from src.core.config import settings
from src.util.datetime_utils import aware_utcnow

# ── Access tokens ──────────────────────────────────────────────────────────────


def create_access_token(
    user_id: uuid.UUID,
    role: str,
    expires_delta: timedelta | None = None,
) -> str:
    """Gera um JWT de acesso para o usuário autenticado.

    Args:
        user_id: UUID do usuário.
        role: papel do usuário (ORGANIZER, CLIENT, GATEKEEPER).
        expires_delta: duração de validade (padrão: JWT_ACCESS_TOKEN_EXPIRE_MINUTES).

    Returns:
        Token JWT assinado como string.
    """
    now = aware_utcnow()
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.jwt_access_token_expire_minutes)
    expire = now + expires_delta
    payload: dict[str, Any] = {
        "sub": str(user_id),
        "role": role,
        "iat": now,
        "exp": expire,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict[str, Any]:
    """Decodifica e valida um JWT de acesso.

    Raises:
        ValueError: se o token estiver expirado ou inválido.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )
    except jwt.ExpiredSignatureError as exc:
        raise ValueError("Token expirado") from exc
    except jwt.InvalidTokenError as exc:
        raise ValueError("Token inválido") from exc
    return payload


# ── QR Code tokens ─────────────────────────────────────────────────────────────


def create_qr_token(ticket_id: uuid.UUID, event_id: uuid.UUID) -> str:
    """Gera um JWT assinado para embutir no QR Code do ingresso.

    O token contém `ticket_id` e `event_id`, tornando-o verificável e
    infalsificável. Nunca inclui dados brutos navegáveis (ID sequencial, preço, etc).

    Args:
        ticket_id: UUID do ingresso.
        event_id: UUID do evento ao qual o ingresso pertence.

    Returns:
        Token JWT assinado como string (sem expiração — o status do ingresso
        é o critério de validade na portaria).
    """
    now = aware_utcnow()
    payload: dict[str, Any] = {
        "sub": "qr_ticket",
        "ticket_id": str(ticket_id),
        "event_id": str(event_id),
        "iat": now,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def decode_qr_token(token: str) -> dict[str, Any]:
    """Decodifica e valida um QR Code token.

    Raises:
        ValueError: se o token estiver corrompido ou com assinatura inválida.
    """
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
            options={"verify_exp": False},  # QR tokens não têm expiração
        )
    except jwt.InvalidTokenError as exc:
        raise ValueError("QR Code token inválido") from exc
    if payload.get("sub") != "qr_ticket":
        raise ValueError("Token não é um QR Code válido")
    return payload
