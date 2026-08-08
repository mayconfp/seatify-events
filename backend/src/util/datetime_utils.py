"""Utilitários de data e hora para toda a aplicação.

Regra única: todo datetime escrito num campo de banco ou comparado em lógica
de negócio deve ser tz-aware UTC. A localização acontece apenas na borda
(frontend / agendamentos por entidade).
"""

from datetime import UTC, date, datetime, timedelta
from typing import Annotated
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
import logging

from pydantic import PlainSerializer

logger = logging.getLogger(__name__)

# No Windows, ZoneInfo("UTC") requer o pacote `tzdata` instalado.
# Usamos o utc do módulo datetime como fallback seguro.
try:
    UTC_ZONE = ZoneInfo("UTC")
except ZoneInfoNotFoundError:
    UTC_ZONE = UTC  # type: ignore[assignment]


def aware_utcnow() -> datetime:
    """Hora atual em UTC, tz-aware.

    Esta é a única fonte de "agora" no backend. Use sempre que precisar
    registrar ou comparar um instante de tempo.
    """
    return datetime.now(UTC)


def ensure_aware_utc(value: datetime) -> datetime:
    """Converte um datetime para UTC tz-aware.

    Um datetime naive é assumido como UTC (contrato histórico de storage) e
    apenas recebe o tzinfo; um datetime aware em outro fuso é convertido.
    """
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def naive_utcnow() -> datetime:
    """Hora atual UTC como datetime naive.

    Use apenas para colunas legadas tz-naive. Novas colunas devem ser
    tz-aware e usar `aware_utcnow()`.
    """
    return datetime.now(UTC).replace(tzinfo=None)


def resolve_zone(name: str | None) -> ZoneInfo:
    """Fuso horário de um workspace/entidade.

    Um nome inválido ou vazio cai para UTC com aviso, garantindo que um erro
    de configuração nunca derrube um fluxo inteiro.
    """
    if not name:
        return UTC_ZONE
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError):
        logger.warning("Fuso inválido '%s'; usando UTC", name)
        return UTC_ZONE


def local_date(value: datetime, zone: ZoneInfo) -> date:
    """Dia de calendário de `value` no fuso `zone`."""
    return ensure_aware_utc(value).astimezone(zone).date()


# Tipo reutilizável para campos datetime em schemas de resposta.
# Serializa sempre com offset UTC, mesmo se um valor naive escapar.
UtcDatetime = Annotated[datetime, PlainSerializer(ensure_aware_utc, return_type=datetime)]


def generate_expires_at_from_expires_in(expires_in: int) -> int:
    """Converte duração em segundos para timestamp Unix de expiração."""
    expires_at_datetime = datetime.now(UTC) + timedelta(seconds=expires_in)
    return int(expires_at_datetime.timestamp())


def is_expired(expires_at: int, skew_minutes: int = 10) -> bool:
    """Verifica se um timestamp Unix de expiração já passou (com margem)."""
    expires_at_datetime = datetime.fromtimestamp(expires_at, UTC)
    return datetime.now(UTC) >= (expires_at_datetime - timedelta(minutes=skew_minutes))
