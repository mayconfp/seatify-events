"""Alembic env.py — suporte a migrações assíncronas com AsyncPG.

`_database_url()` lê o DATABASE_URL diretamente do ambiente ou do .env,
sem instanciar `Settings` completo. Isso desacopla as migrações da config
da aplicação: `uv run alembic upgrade head` funciona mesmo que outros campos
obrigatórios do Settings não estejam disponíveis no ambiente de migração.

O `import src.db.registry` popula o `Base.metadata` com todos os modelos
antes do autogenerate, garantindo que nenhum modelo seja perdido.
"""

import asyncio
import os
from logging.config import fileConfig
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

import src.db.registry  # noqa: F401 — registra todos os modelos no Base.metadata
from alembic import context
from src.db.base import Base


def _database_url() -> str:
    """Resolve DATABASE_URL sem depender do Settings completo.

    Ordem de busca:
    1. Variável de ambiente DATABASE_URL.
    2. Arquivo .env na raiz do projeto (dois níveis acima de backend/alembic/).
    """
    url = os.environ.get("DATABASE_URL")
    if not url:
        # Caminho: backend/alembic/env.py → backend/ → project_root/.env
        env_file = Path(__file__).resolve().parents[2] / ".env"
        if env_file.is_file():
            url = dotenv_values(env_file).get("DATABASE_URL")
    if not url:
        raise RuntimeError(
            "DATABASE_URL não está definido — exporte a variável ou adicione-a ao .env "
            "para que o Alembic consiga conectar ao banco."
        )
    return url


# Configuração Alembic

config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", _database_url())


#Migrations offline


def run_migrations_offline() -> None:
    """Modo offline: gera SQL sem conexão com o banco."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


# Migrations online (async)


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Cria a engine async e executa as migrações online."""
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    """Ponto de entrada para migrações online (modo padrão)."""
    loop = asyncio.SelectorEventLoop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(run_async_migrations())
    finally:
        loop.close()


# Dispatch

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
