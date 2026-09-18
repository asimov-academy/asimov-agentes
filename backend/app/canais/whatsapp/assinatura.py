"""Assinatura do webhook da Meta: HMAC SHA-256 do corpo cru, no header `X-Hub-Signature-256`.

A chave é o `app_secret` do app da Meta, guardado cifrado nas credenciais do agente. O header vem
no formato `sha256=<hex>`. Sem header ou com assinatura diferente, o webhook é recusado com 401: a
Meta repete a entrega, e ao contrário do Chatwoot não silencia nada por causa disso.
"""

import hashlib
import hmac

PREFIXO = "sha256="


def assina(app_secret: str, corpo: bytes) -> str:
    return PREFIXO + hmac.new(app_secret.encode(), corpo, hashlib.sha256).hexdigest()


def assinatura_confere(app_secret: str, assinatura: str, corpo: bytes) -> bool:
    if not app_secret or not assinatura:
        return False
    return hmac.compare_digest(assina(app_secret, corpo), assinatura.strip().lower())
