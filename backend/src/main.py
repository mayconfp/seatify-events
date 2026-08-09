"""Ponto de entrada da aplicação FastAPI

Registra routers dinamicamente de src/module/ (qualquer handler.py com
router), configura CORS restrito, security headers OWASP, validação de
segredos no startup e expõe /healthz.
"""

import importlib
import logging
import pkgutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from src.core.config import settings, validate_critical_secrets
from src.db.session import sessionmanager
from src.deps import limiter

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
    """Percorre src/module/ e monta o router de cada handler.py.

    O registro acontece na construção do app (não no lifespan): um seeder
    que falhe não deve derrubar a tabela de rotas inteira.
    """
    search_paths = [str(p) for p in importlib.import_module(_MODULE_PKG).__path__]

    for _, name, is_pkg in pkgutil.iter_modules(search_paths):
        if not is_pkg:
            continue
        # Tenta handler de nível superior: src.module.<name>.handler
        try:
            handler_module = importlib.import_module(f"{_MODULE_PKG}.{name}.handler")
            router = getattr(handler_module, "router", None)
            if router is not None:
                app.include_router(router)
                logger.info("Router registrado: %s", name)
        except Exception as exc:
            logger.warning("Falha ao registrar router %s: %s", name, exc)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Ciclo de vida da aplicação: inicialização e teardown.

    A validação de segredos críticos roda ANTES do yield: se algum segredo
    for fraco ou curto demais, a API não sobe.
    """
    logger.info("Eventify API iniciando...")
    try:
        validate_critical_secrets(settings)
    except RuntimeError as exc:
        logger.critical("Startup abortado — %s", exc)
        raise
    logger.info("Segredos críticos validados com sucesso.")
    yield
    # Teardown: fecha a engine async graciosamente
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

    # Rate limiting: registra o limiter no estado do app e o handler de 429.
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
