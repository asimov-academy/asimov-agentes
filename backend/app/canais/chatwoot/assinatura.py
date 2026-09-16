"""Assinatura do webhook de Agent Bot do Chatwoot.

Em `lib/webhooks/trigger.rb` o Chatwoot assina `"{timestamp}.{corpo_cru}"`, não só o corpo:

    "sha256=#{OpenSSL::HMAC.hexdigest('SHA256', @secret, "#{ts}.#{body}")}"

O corpo tem de ser os bytes recebidos; reserializar o JSON muda a assinatura.
"""

import hashlib
import hmac
import time

TOLERANCIA_SEGUNDOS = 300


def assinatura_confere(secret: str, timestamp: str, assinatura: str, corpo: bytes) -> bool:
    if not secret or not timestamp or not assinatura:
        return False
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + corpo, hashlib.sha256)
    return hmac.compare_digest(f"sha256={mac.hexdigest()}", assinatura)


def timestamp_recente(timestamp: str, agora: float | None = None) -> bool:
    """Recusa replay de payload capturado."""
    try:
        ts = int(timestamp)
    except (TypeError, ValueError):
        return False
    agora = time.time() if agora is None else agora
    return abs(agora - ts) <= TOLERANCIA_SEGUNDOS


def assina(secret: str, corpo: bytes, timestamp: str) -> str:
    """Mesma conta do Chatwoot. Usado nos testes e no diagnóstico do setup."""
    mac = hmac.new(secret.encode(), f"{timestamp}.".encode() + corpo, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"
