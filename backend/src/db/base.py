"""Base declarativa SQLAlchemy + mixin compartilhado para todos os modelos.

Todo modelo ORM do projeto importa BaseModel daqui. Os arquivos de modelo
ficam em seus respectivos módulos (src/module/<nome>/model.py) e são
registrados no Base.metadata via src/db/registry.py.

Padrões implementados (espelhando a reference_architeture/):
- UTCDateTime: TypeDecorator que garante datetimes tz-aware UTC de ponta a ponta.
- varchar_enum(): helper para enums VARCHAR não usa tipo nativo Postgres.
- NAMING_CONVENTION: nomes determinísticos para PKs, FKs, UQs e índices.
- BaseModel: classe abstrata com UUID PK + timestamps de auditoria.
"""

from __future__ import annotations

import enum
import uuid
from datetime import UTC, datetime
from typing import Any, override

from sqlalchemy import DateTime, MetaData
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, declarative_base, mapped_column
from sqlalchemy.types import TypeDecorator

from src.util.datetime_utils import aware_utcnow as _utcnow


class UTCDateTime(TypeDecorator[datetime]):
    """Datetime tz-aware UTC normalizado na entrada e na saída.

    Em Postgres mapeia para ``timestamptz``. Garante que valores sejam sempre
    UTC tz-aware independente do backend:
    - No bind: valor naive é marcado como UTC; valor aware é convertido para UTC.
    - No read: valor que voltar naive (ex.: SQLite em testes) é marcado UTC.
    """

    impl = DateTime(timezone=True)
    cache_ok = True

    @override
    def process_bind_param(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @override
    def process_result_value(self, value: datetime | None, dialect: Any) -> datetime | None:
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)


def varchar_enum(enum_cls: type[enum.Enum], *, name: str, length: int | None = None) -> SQLEnum:
    """Enum armazenado como VARCHAR — nunca como tipo nativo Postgres.

    Tipos nativos causam DuplicateObjectError em CREATE TYPE quando o
    Alembic tenta recriar a tabela. Guardar o .value (não o .name) mantém
    o banco idêntico ao que a API serializa na wire.
    """
    values = [str(member.value) for member in enum_cls]
    return SQLEnum(
        enum_cls,
        name=name,
        native_enum=False,
        length=length or max(len(v) for v in values),
        values_callable=lambda e: [str(member.value) for member in e],
    )


# Convenção de nomes determinística para constraints.
# Sem isso o Postgres auto-nomeia FKs/UQs, impossibilitando drops futuros.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s",
    "pk": "pk_%(table_name)s",
}

# Toda coluna Mapped[datetime] mapeia para UTCDateTime por padrão.
Base = declarative_base(
    type_annotation_map={datetime: UTCDateTime()},
    metadata=MetaData(naming_convention=NAMING_CONVENTION),
)


class BaseModel(Base):
    """Base abstrata para todos os modelos persistidos.

    Fornece UUID PK + timestamps de auditoria. Subclasses definem
    __tablename__ e colunas adicionais.
    """

    __abstract__ = True

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    created_at: Mapped[datetime] = mapped_column(default=_utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        default=_utcnow, onupdate=_utcnow, nullable=False
    )
    deleted_at: Mapped[datetime | None] = mapped_column(nullable=True)
