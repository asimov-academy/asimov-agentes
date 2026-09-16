"""Credenciais de canal e token de webhook guardados cifrados.

O token de webhook tem duas formas no banco: o hash, para achar o agente pela URL sem
guardar o token em claro, e a versão cifrada, para o menu mostrar a URL de novo.
"""

import hashlib
import json
import secrets
from typing import Any

from cryptography.fernet import Fernet

from app.plataforma.config import config


def _fernet() -> Fernet:
    return Fernet(config().chave_criptografia.encode())


def cifra(dados: dict[str, Any]) -> str:
    return _fernet().encrypt(json.dumps(dados).encode()).decode()


def decifra(texto: str) -> dict[str, Any]:
    return json.loads(_fernet().decrypt(texto.encode()))


def cifra_texto(texto: str) -> str:
    return _fernet().encrypt(texto.encode()).decode()


def decifra_texto(texto: str) -> str:
    return _fernet().decrypt(texto.encode()).decode()


def novo_token() -> str:
    return secrets.token_urlsafe(32)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def mascara(valor: str) -> str:
    """Só os 4 últimos caracteres, para o menu conferir qual credencial está gravada."""
    return f"****{valor[-4:]}" if len(valor) > 4 else "****"
