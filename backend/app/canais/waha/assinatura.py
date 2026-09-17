"""Assinatura do webhook da WAHA: HMAC SHA-512 do corpo cru, no header `X-Webhook-Hmac`.

A chave é sorteada por agente na conexão e vai na configuração da sessão. Sem header ou com
assinatura diferente, o webhook é recusado: a WAHA é local e não pune resposta de erro.
"""

import hashlib
import hmac


def assina(chave: str, corpo: bytes) -> str:
    return hmac.new(chave.encode(), corpo, hashlib.sha512).hexdigest()


def assinatura_confere(chave: str, assinatura: str, corpo: bytes) -> bool:
    if not chave or not assinatura:
        return False
    return hmac.compare_digest(assina(chave, corpo), assinatura.strip().lower())
