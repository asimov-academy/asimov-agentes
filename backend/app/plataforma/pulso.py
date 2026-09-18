"""Sinal de vida do worker, lido pelo `/health`.

API saudável com worker parado é a instalação inteira muda: a mensagem chega, é gravada e ninguém
responde (auditoria de 2026-09-18, A20). O worker bate o pulso ao subir e de minuto em minuto; a
API só lê. Fica aqui, e não em `worker.py`, para a API não importar o worker inteiro só por duas
constantes.
"""

import time
from typing import Any

CHAVE_PULSO = "worker:pulso"
CHAVE_JA_SUBIU = "worker:ja_subiu"
# Vale mais que o intervalo do cron: um minuto atrasado não pode virar alarme.
PULSO_SEGUNDOS = 180


async def bate(redis: Any) -> None:
    await redis.set(CHAVE_PULSO, str(int(time.time())), ex=PULSO_SEGUNDOS)
    await redis.set(CHAVE_JA_SUBIU, "1")


async def estado(redis: Any) -> str:
    """`ok`, `parado` ou `aguardando` (instalação que ainda não viu o worker subir nenhuma vez)."""
    if await redis.exists(CHAVE_PULSO):
        return "ok"
    return "parado" if await redis.exists(CHAVE_JA_SUBIU) else "aguardando"
