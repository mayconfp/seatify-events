"""Hashing e verificação de senhas via PBKDF2-SHA256.

Usa salt aleatório de 16 bytes por senha. O formato armazenado é:
`<salt_hex>$<hash_hex>`.
"""

import hashlib
import hmac
import os

_PBKDF2_ITERATIONS = 100_000


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Deriva e retorna o hash da senha no formato `salt_hex$hash_hex`.

    Args:
        password: senha em plaintext.
        salt: salt opcional (gerado aleatoriamente se omitido).

    Returns:
        String no formato `<salt_hex>$<hash_hex>`.
    """
    if salt is None:
        salt = os.urandom(16)
    hash_bytes = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return f"{salt.hex()}${hash_bytes.hex()}"


def is_valid_password_hash(password: str, hashed: str) -> bool:
    """Verifica se `password` corresponde ao hash armazenado.

    Usa `hmac.compare_digest` para evitar timing attacks.

    Args:
        password: senha em plaintext a verificar.
        hashed: hash armazenado no formato `salt_hex$hash_hex`.

    Returns:
        `True` se a senha bater com o hash, `False` caso contrário.
    """
    try:
        salt_hex, hash_hex = hashed.split("$")
        salt = bytes.fromhex(salt_hex)
        expected_hash = bytes.fromhex(hash_hex)
    except ValueError:
        return False
    test_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, _PBKDF2_ITERATIONS)
    return hmac.compare_digest(test_hash, expected_hash)
