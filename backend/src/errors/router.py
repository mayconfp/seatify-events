"""Funções auxiliares para exceções HTTP padronizadas.

Routers devem sempre levantar exceções via estas funções,
nunca construindo HTTPException diretamente. Isso garante mensagens
de erro consistentes.
"""

from typing import NoReturn

from fastapi import HTTPException, status


def validation_error(detail: str) -> HTTPException:
    """400 Bad Request - entrada inválida ou regra de negócio violada."""
    return HTTPException(detail=detail, status_code=status.HTTP_400_BAD_REQUEST)


def unauthorized_error(detail: str = "Não autenticado") -> HTTPException:
    """401 Unauthorized - ausência ou invalidade do token de autenticação."""
    return HTTPException(
        detail=detail,
        status_code=status.HTTP_401_UNAUTHORIZED,
        headers={"WWW-Authenticate": "Bearer"},
    )


def forbidden_error(
    detail: str = "Você não tem permissão para realizar esta ação.",
) -> HTTPException:
    """403 Forbidden — usuário autenticado mas sem permissão para o recurso."""
    return HTTPException(detail=detail, status_code=status.HTTP_403_FORBIDDEN)


def not_found_error(detail: str = "Recurso não encontrado") -> HTTPException:
    """404 Not Found — recurso inexistente ou soft-deleted."""
    return HTTPException(detail=detail, status_code=status.HTTP_404_NOT_FOUND)


def conflict_error(detail: str = "Conflito") -> HTTPException:
    """409 Conflict — violação de unicidade ou estado inconsistente."""
    return HTTPException(detail=detail, status_code=status.HTTP_409_CONFLICT)


def too_many_requests_error(detail: str = "Muitas requisições") -> HTTPException:
    """429 Too Many Requests."""
    return HTTPException(detail=detail, status_code=status.HTTP_429_TOO_MANY_REQUESTS)


def exception_template(exc: Exception, prefix: str) -> NoReturn:
    """Propaga HTTPException ou encapsula exceções inesperadas em 500."""
    if isinstance(exc, HTTPException):
        raise exc
    raise HTTPException(status_code=500, detail=f"{prefix}: {exc}")
