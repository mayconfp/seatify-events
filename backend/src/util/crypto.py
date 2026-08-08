"""Criptografia simétrica via Fernet para dados em repouso.

A chave Fernet é derivada do `FERNET_SECRET` via SHA-256: o SHA-256 produz
32 bytes — exatamente o que o Fernet precisa — e o base64url-encode gera a
chave de 44 chars no formato esperado.

Use sempre que precisar persistir um segredo que será lido de volta
(ex.: tokens de QR Code em repouso, dados sensíveis).
"""

import base64
import hashlib

from cryptography.fernet import Fernet

from src.core.config import settings

_fernet = Fernet(
    base64.urlsafe_b64encode(hashlib.sha256(settings.fernet_secret.encode()).digest())
)


def encrypt_secret(plaintext: str) -> str:
    """Criptografa uma string e retorna o ciphertext como string."""
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_secret(ciphertext: str) -> str:
    """Descriptografa um ciphertext e retorna o plaintext como string."""
    return _fernet.decrypt(ciphertext.encode()).decode()
