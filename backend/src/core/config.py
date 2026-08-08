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
