"""Ponto de entrada da aplicação FastAPI

Registra routers dinamicamente de src/module/ (qualquer handler.py com
router), configura CORS e expõe /healthz.
"""

import importlib
import logging
import pkgutil
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.db.session import sessionmanager

logger = logging.getLogger(__name__)

_MODULE_PKG = "src.module"


def _register_module_routers(app: FastAPI) -> None:
    """Percorre src/module/ e monta o router de cada handler.py.

    O registro acontece na construção do app (não no lifespan): um seeder
    que falhe não deve derrubar a tabela de rotas inteira.
    """
    search_paths = [str(p) for p in importlib.import_module(_MODULE_PKG).__path__]

    for _, name, _ in pkgutil.iter_modules(search_paths):
        # Tenta handler de nível superior: src.module.<name>.handler
        try:
            handler_module = importlib.import_module(f"{_MODULE_PKG}.{name}.handler")
            router = getattr(handler_module, "router", None)
            if router is not None:
                app.include_router(router)
                logger.debug("Router registrado: %s.handler", name)
                continue
        except (ModuleNotFoundError, AttributeError):
            pass

        # Fallback: sub-módulos (ex: src.module.<name>.<sub>.handler)
        sub_paths = [str(Path(p) / name) for p in search_paths]
        for _, sub, _ in pkgutil.iter_modules(sub_paths):
            try:
                sub_handler = importlib.import_module(f"{_MODULE_PKG}.{name}.{sub}.handler")
                sub_router = getattr(sub_handler, "router", None)
                if sub_router is not None:
                    app.include_router(sub_router)
                    logger.debug("Router registrado: %s.%s.handler", name, sub)
            except (ModuleNotFoundError, AttributeError):
                pass


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Ciclo de vida da aplicação: inicialização e teardown."""
    logger.info("Eventify API iniciando...")
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

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
        allow_credentials=True,
    )

    @app.get("/healthz", tags=["Health"])
    async def healthz():  # pyright: ignore[reportUnusedFunction]
        """Verifica se a API está no ar."""
        return {"status": "ok"}

    # Registra todos os routers dos módulos dinamicamente
    _register_module_routers(app)

    return app


app = create_app()
