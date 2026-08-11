"""Ponto de entrada da aplicação FastAPI

Registra routers dinamicamente de src/module/ (qualquer router.py com
router), configura CORS restrito, security headers OWASP, validação de
segredos no startup e expõe /healthz.
"""

import asyncio
import importlib
import logging
import pkgutil
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from sqlalchemy import select

from src.core.config import settings, validate_critical_secrets
from src.db.session import sessionmanager
from src.deps import limiter
from src.module.events.model import Event
from src.module.tickets.service import _release_expired_pending_seats
from src.util.datetime_utils import aware_utcnow

logger = logging.getLogger(__name__)

_MODULE_PKG = "src.module"

# Cabeçalhos de segurança OWASP aplicados a todas as respostas da API.
SECURITY_HEADERS: dict[str, str] = {
    "Strict-Transport-Security": "max-age=31536000; includeSubDomains",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Content-Security-Policy": "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net; style-src 'self' 'unsafe-inline' https://cdn.jsdelivr.net; img-src 'self' data: https://fastapi.tiangolo.com",
    "X-XSS-Protection": "1; mode=block",
}


def _register_module_routers(app: FastAPI) -> None:
    """Percorre src/module/ e monta o router de cada router.py.

    O registro acontece na construção do app (não no lifespan): um seeder
    que falhe não deve derrubar a tabela de rotas inteira.
    """
    search_paths = [str(p) for p in importlib.import_module(_MODULE_PKG).__path__]

    for _, name, is_pkg in pkgutil.iter_modules(search_paths):
        if not is_pkg:
            continue
        # Tenta router de nível superior: src.module.<name>.router
        try:
            router_module = importlib.import_module(f"{_MODULE_PKG}.{name}.router")
            router = getattr(router_module, "router", None)
            if router is not None:
                app.include_router(router)
                logger.info("Router registrado: %s", name)
        except Exception as exc:
            logger.warning("Falha ao registrar router %s: %s", name, exc)


async def _periodic_cleanup_task():
    """Task interna que roda a cada 5 minutos para limpar assentos expirados.
    
    Varre eventos futuros (ainda nao ocorridos) e libera assentos PENDING
    que ultrapassaram o timeout de 15 minutos. Consome recursos minimos
    (asyncio.sleep nao bloqueia CPU) e e adequado para hospedagem gratuita.
    """
    while True:
        await asyncio.sleep(60 * 5)  # Roda a cada 5 minutos
        try:
            async with sessionmanager.session() as session:
                # Busca eventos futuros (ainda nao ocorridos)
                result = await session.execute(
                    select(Event.id).where(
                        Event.deleted_at.is_(None),
                        Event.event_date >= aware_utcnow(),
                    )
                )
                event_ids = [row[0] for row in result.all()]
                
                # Libera assentos expirados de cada evento futuro
                for event_id in event_ids:
                    released = await _release_expired_pending_seats(session, event_id)
                    if released > 0:
                        logger.info(
                            "Limpeza periodica: %d assentos liberados no evento %s",
                            released,
                            event_id,
                        )
        except Exception as exc:
            logger.error("Erro na limpeza periodica de assentos: %s", exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Ciclo de vida da aplicação: inicialização e teardown.

    A validação de segredos críticos roda ANTES do yield: se algum segredo
    for fraco ou curto demais, a API não sobe. Tambem inicia a task de
    limpeza periodica de assentos expirados em background.
    """
    logger.info("Eventify API iniciando...")
    try:
        validate_critical_secrets(settings)
    except RuntimeError as exc:
        logger.critical("Startup abortado — %s", exc)
        raise
    logger.info("Segredos críticos validados com sucesso.")
    
    # Inicia a task de limpeza periodica em background
    cleanup_task = asyncio.create_task(_periodic_cleanup_task())
    logger.info("Task de limpeza periodica iniciada (intervalo: 5 minutos).")
    
    yield
    
    # Teardown: cancela a task de limpeza e fecha a engine async
    cleanup_task.cancel()
    try:
        await cleanup_task
    except asyncio.CancelledError:
        logger.info("Task de limpeza periodica cancelada.")
    
    if sessionmanager._engine is not None:
        await sessionmanager.close()
    logger.info("Eventify API encerrada.")


def create_app() -> FastAPI:
    """Factory da aplicação FastAPI."""
    app = FastAPI(
        lifespan=lifespan,
        title="Eventify API",
        description="Plataforma de Gestão de Eventos, Reserva de Assentos e Ingressos",
        version="1.0.0",
        contact={
            "name": "Eventify",
            "url": "https://github.com/eventify",
        },
    )

    # Rate limiting: registra o limiter no estado do app e o exception handler de 429.
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

    # CORS restrito: apenas a origem do front-end configurada no .env.
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[settings.frontend_url],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    @app.middleware("http")
    async def security_headers_middleware(  # pyright: ignore[reportUnusedFunction]
        request: Request,
        call_next,
    ) -> Response:
        """Injeta os cabeçalhos de segurança OWASP em todas as respostas."""
        response: Response = await call_next(request)
        for header_name, header_value in SECURITY_HEADERS.items():
            response.headers[header_name] = header_value
        return response

    @app.get("/healthz", tags=["Health"])
    async def healthz():  # pyright: ignore[reportUnusedFunction]
        """Verifica se a API está no ar."""
        return {"status": "ok"}

    # Registra todos os routers dos módulos dinamicamente
    _register_module_routers(app)

    return app


app = create_app()
