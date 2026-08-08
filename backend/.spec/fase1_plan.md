# Fase 1 — Plano de Implementação: Backend Foundation

## Objetivo
Construir o esqueleto completo da API FastAPI com ORM SQLAlchemy 2.0, migrações Alembic, seed inicial e testes básicos de integração.

## Estrutura de Arquivos Criados

```
backend/
├── alembic/
│   ├── env.py            ← Migrações async; _database_url() autônomo
│   ├── script.py.mako    ← Template de migration
│   └── README
├── alembic.ini           ← Configuração Alembic
├── pytest.ini            ← asyncio_mode=auto
├── run_seed.py           ← Seed idempotente (4 users, 1 evento, 20 seats)
├── src/
│   ├── main.py           ← FastAPI app factory + dynamic router registration
│   ├── deps.py           ← SessionDep, LoggedUserDep, require_role()
│   ├── core/
│   │   └── config.py     ← Settings (pydantic-settings) lendo ../.env
│   ├── db/
│   │   ├── base.py       ← UTCDateTime, varchar_enum, BaseModel abstrato
│   │   ├── session.py    ← DatabaseSessionManager (expire_on_commit=False)
│   │   └── registry.py   ← Importa todos os modelos para Base.metadata
│   ├── errors/
│   │   └── router.py     ← validation_error, not_found_error, forbidden_error...
│   ├── util/
│   │   ├── datetime_utils.py  ← aware_utcnow(), UtcDatetime
│   │   ├── crypto.py          ← Fernet (SHA-256 do FERNET_SECRET)
│   │   ├── jwt_utils.py       ← create_access_token, create_qr_token, decode_*
│   │   └── password_digest.py ← PBKDF2-SHA256 hash/verify
│   └── module/
│       ├── auth/model.py      ← UserRole enum, User ORM
│       ├── events/model.py    ← EventType enum, Event ORM
│       ├── tickets/model.py   ← SeatStatus, TicketStatus, Seat, Ticket ORM
│       └── checkout/model.py  ← ProcessedWebhookEvent ORM
└── tests/
    ├── conftest.py       ← AsyncClient fixture (ASGITransport)
    ├── test_health.py    ← GET /healthz → 200 OK
    ├── test_auth.py      ← password hash + JWT claims
    └── test_tickets.py   ← QR token creation, tamper detection, stability
```

## Padrões Arquiteturais Aplicados

| Padrão | Implementação |
|---|---|
| UTCDateTime | TypeDecorator em `db/base.py` — normaliza naive→aware |
| varchar_enum | Enums como VARCHAR, nunca tipo nativo Postgres |
| expire_on_commit=False | `DatabaseSessionManager` — evita MissingGreenlet |
| _database_url() autônomo | `alembic/env.py` — desacoplado do Settings completo |
| Dynamic router registration | `_register_module_routers()` em `main.py` |
| QR token infalsificável | JWT assinado com sub="qr_ticket" + ticket_id + event_id |
| RBAC via require_role() | Factory de dependência retorna 403 para papel errado |
| with_for_update() | Documentado no Seat model — obrigatório em reservas |

## Credenciais de Seed

| Email | Senha | Papel |
|---|---|---|
| organizer@eventify.com | Organizer@2026 | ORGANIZER |
| client1@eventify.com | Client1@2026 | CLIENT |
| client2@eventify.com | Client2@2026 | CLIENT |
| gatekeeper@eventify.com | Gatekeeper@2026 | GATEKEEPER |

## Comandos de Verificação

```bash
# 1. Gerar e aplicar migração inicial
cd backend/
uv run alembic revision --autogenerate -m "Initial schema"
uv run alembic upgrade head

# 2. Popular banco com dados de seed
uv run python run_seed.py

# 3. Executar testes
uv run pytest tests/ -v

# 4. Iniciar servidor de desenvolvimento
uv run fastapi dev src/main.py
```
