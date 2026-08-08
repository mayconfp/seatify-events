"""Script de seed inicial — Eventify 2026.

Popula o banco com os dados mínimos exigidos pelo edital:
  - 1 Organizador  : organizer@eventify.com  / senha: Organizer@2026
  - 2 Clientes     : client1@eventify.com    / senha: Client1@2026
                     client2@eventify.com    / senha: Client2@2026
  - 1 Portaria     : gatekeeper@eventify.com / senha: Gatekeeper@2026
  - 1 Evento SEATED de teste com 20 assentos disponíveis (A1–A20)

Execute a partir da raiz de backend/:
    uv run python run_seed.py

O script é idempotente: verifica a existência de cada entidade pelo email
ou por campos únicos antes de inserir, evitando duplicatas em re-execuções.
"""

import asyncio
import sys
from datetime import timedelta
from decimal import Decimal

# Garante que src.* seja importável mesmo ao rodar da raiz de backend/
sys.path.insert(0, ".")

from src.core.config import settings  # noqa: E402 — sys.path precisa estar configurado
from src.db.session import sessionmanager  # noqa: E402
from src.module.auth.model import User, UserRole  # noqa: E402
from src.module.events.model import Event, EventType  # noqa: E402
from src.module.tickets.model import Seat, SeatStatus  # noqa: E402
from src.util.datetime_utils import aware_utcnow  # noqa: E402
from src.util.password_digest import hash_password  # noqa: E402

from sqlalchemy import select  # noqa: E402

# ── Dados de seed ──────────────────────────────────────────────────────────────

SEED_USERS = [
    {
        "name": "Organizador Eventify",
        "email": "organizer@eventify.com",
        "password": "Organizer@2026",
        "role": UserRole.ORGANIZER,
    },
    {
        "name": "Cliente 1",
        "email": "client1@eventify.com",
        "password": "Client1@2026",
        "role": UserRole.CLIENT,
    },
    {
        "name": "Cliente 2",
        "email": "client2@eventify.com",
        "password": "Client2@2026",
        "role": UserRole.CLIENT,
    },
    {
        "name": "Portaria Eventify",
        "email": "gatekeeper@eventify.com",
        "password": "Gatekeeper@2026",
        "role": UserRole.GATEKEEPER,
    },
]

EVENT_DATA = {
    "title": "Show de Teste — Eventify Music Fest",
    "description": "Evento de demonstração da plataforma Eventify 2026.",
    "venue_name": "Arena Eventify",
    "capacity": 20,
    "price": Decimal("99.90"),
    "type": EventType.SEATED,
    "external_tmdb_id": None,
    "poster_url": None,
}

SEAT_COUNT = 20
SEAT_PREFIX = "A"


# Funções de seed


async def seed_users(session) -> dict[str, User]:
    """Cria usuários de seed se ainda não existirem. Retorna mapa email→User."""
    created: dict[str, User] = {}
    for user_data in SEED_USERS:
        result = await session.execute(
            select(User).where(User.email == user_data["email"])
        )
        existing = result.scalar_one_or_none()
        if existing:
            print(f"  [skip] Usuário já existe: {user_data['email']}")
            created[user_data["email"]] = existing
            continue

        user = User(
            name=user_data["name"],
            email=user_data["email"],
            password_digest=hash_password(user_data["password"]),
            role=user_data["role"],
        )
        session.add(user)
        await session.flush()  # obtém o id sem commit
        created[user_data["email"]] = user
        print(f"  [+] Usuário criado: {user_data['email']} ({user_data['role'].value})")

    return created


async def seed_event(session, organizer: User) -> Event:
    """Cria o evento de teste se ainda não existir."""
    result = await session.execute(
        select(Event).where(Event.title == EVENT_DATA["title"])
    )
    existing = result.scalar_one_or_none()
    if existing:
        print(f"  [skip] Evento já existe: {EVENT_DATA['title']}")
        return existing

    event = Event(
        organizer_id=organizer.id,
        title=EVENT_DATA["title"],
        description=EVENT_DATA["description"],
        venue_name=EVENT_DATA["venue_name"],
        capacity=EVENT_DATA["capacity"],
        price=EVENT_DATA["price"],
        type=EVENT_DATA["type"],
        external_tmdb_id=EVENT_DATA["external_tmdb_id"],
        poster_url=EVENT_DATA["poster_url"],
        event_date=aware_utcnow() + timedelta(days=30),
    )
    session.add(event)
    await session.flush()
    print(f"  [+] Evento criado: {event.title} (id={event.id})")
    return event


async def seed_seats(session, event: Event) -> None:
    """Cria assentos AVAILABLE para o evento se ainda não existirem."""
    result = await session.execute(
        select(Seat).where(Seat.event_id == event.id)
    )
    existing_seats = result.scalars().all()
    if existing_seats:
        print(f"  [skip] Assentos já existem para o evento ({len(existing_seats)} seats)")
        return

    seats = [
        Seat(
            event_id=event.id,
            seat_number=f"{SEAT_PREFIX}{i}",
            status=SeatStatus.AVAILABLE,
            user_id=None,
        )
        for i in range(1, SEAT_COUNT + 1)
    ]
    session.add_all(seats)
    await session.flush()
    print(f"  [+] {SEAT_COUNT} assentos criados: {SEAT_PREFIX}1–{SEAT_PREFIX}{SEAT_COUNT}")


# Entrypoint


async def run_seed() -> None:
    print("\n=== Iniciando seed — Eventify Platform ===\n")
    async with sessionmanager.session() as session:
        print("[*] Criando usuarios...")
        users = await seed_users(session)

        organizer = users["organizer@eventify.com"]

        print("\n[*] Criando evento de teste...")
        event = await seed_event(session, organizer)

        print("\n[*] Criando assentos...")
        await seed_seats(session, event)

        await session.commit()

    print("\n[OK] Seed concluido com sucesso!\n")
    print("Credenciais de acesso:")
    print("  organizer@eventify.com    / Organizer@2026  (ORGANIZER)")
    print("  client1@eventify.com      / Client1@2026    (CLIENT)")
    print("  client2@eventify.com      / Client2@2026    (CLIENT)")
    print("  gatekeeper@eventify.com   / Gatekeeper@2026 (GATEKEEPER)\n")


if __name__ == "__main__":
    asyncio.run(run_seed())
