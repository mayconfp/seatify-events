"""Configuração central da aplicação via pydantic-settings.

Lê variáveis do arquivo .env localizado na raiz do projeto (um nível acima
do diretório backend/). Todas as dependências externas — banco de dados, JWT,
Stripe, TMDB — são declaradas aqui com tipagem estrita.
"""

from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

# Garante que o .env da raiz seja carregado antes que qualquer outro módulo
# tente ler variáveis de ambiente.
_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"
load_dotenv(_ENV_FILE)


class Settings(BaseSettings):
    # Banco de dados
    database_url: str

    # JWT
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 60

    # Criptografia simétrica (Fernet) para tokens de QR Code
    fernet_secret: str

    # Stripe
    stripe_secret_key: str
    stripe_webhook_secret: str | None = None

    # TMDB
    tmdb_read_token: str
    tmdb_base_url: str = "https://api.themoviedb.org/3"

    # Frontend
    frontend_url: str = "http://localhost:5173"

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()


# ── Hardening: validação de segredos críticos no startup ──────────────────────

_MINIMUM_SECRET_LENGTH = 32
_WEAK_SECRET_TERMS = ("secret", "123456", "change_me", "changeme", "password")


def validate_critical_secrets(current_settings: Settings) -> None:
    """Valida comprimento e entropia mínima dos segredos críticos.

    Chamada no lifespan da aplicação: impede a subida da API se algum
    segredo tiver menos de 32 caracteres ou contiver termos padrão fracos
    e previsíveis. Os VALORES dos segredos nunca aparecem na mensagem de
    erro nem nos logs — apenas o nome da variável e o motivo da rejeição.

    Raises:
        RuntimeError: lista de problemas encontrados nos segredos.
    """
    critical_secrets: dict[str, str] = {
        "jwt_secret_key": current_settings.jwt_secret_key,
        "fernet_secret": current_settings.fernet_secret,
    }

    problems: list[str] = []
    for name, value in critical_secrets.items():
        if len(value) < _MINIMUM_SECRET_LENGTH:
            problems.append(
                f"'{name}' possui {len(value)} caracteres "
                f"(mínimo exigido: {_MINIMUM_SECRET_LENGTH})"
            )
        lowered_value = value.lower()
        weak_terms_found = [
            term for term in _WEAK_SECRET_TERMS if term in lowered_value
        ]
        if weak_terms_found:
            problems.append(
                f"'{name}' contém termos fracos/previsíveis: "
                f"{', '.join(weak_terms_found)}"
            )

    if problems:
        raise RuntimeError(
            "Segredos críticos reprovados na validação de segurança — "
            "gere novos valores fortes no .env antes de subir a API: "
            + "; ".join(problems)
        )
