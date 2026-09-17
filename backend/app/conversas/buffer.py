"""Buffer e lock por conversa, no Redis.

Buffer: cada mensagem do contato grava um token novo e agenda o turno para daqui a
`buffer_segundos`. Quando o job acorda, só segue se o token ainda for o último; mensagem
nova durante a espera invalida o job anterior. O contato manda cinco mensagens e recebe
uma resposta.

Lock: impede dois turnos simultâneos na mesma conversa. A liberação confere o token antes
de apagar, para um job lento não derrubar o lock de outro.
"""

import uuid
from typing import Any

from redis.asyncio import Redis

_LIBERA_SE_MEU = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


def _chave_buffer(conversa_id: uuid.UUID) -> str:
    return f"buffer:{conversa_id}"


def _chave_lock(conversa_id: uuid.UUID) -> str:
    return f"lock:{conversa_id}"


async def agenda_turno(
    fila: Any, cliente_id: uuid.UUID, conversa_id: uuid.UUID, buffer_segundos: int
) -> str:
    token = uuid.uuid4().hex
    await fila.set(_chave_buffer(conversa_id), token, ex=max(buffer_segundos * 10, 60))
    await fila.enqueue_job(
        "processar_turno", str(cliente_id), str(conversa_id), token, _defer_by=buffer_segundos
    )
    return token


async def token_ainda_vale(redis: Redis, conversa_id: uuid.UUID, token: str) -> bool:
    atual = await redis.get(_chave_buffer(conversa_id))
    if isinstance(atual, bytes):
        atual = atual.decode()
    return atual == token


async def adquire_lock(redis: Redis, conversa_id: uuid.UUID, token: str, ttl: int) -> bool:
    return bool(await redis.set(_chave_lock(conversa_id), token, nx=True, ex=ttl))


async def turno_em_andamento(redis: Redis, conversa_id: uuid.UUID) -> bool:
    return bool(await redis.exists(_chave_lock(conversa_id)))


async def libera_lock(redis: Redis, conversa_id: uuid.UUID, token: str) -> None:
    await redis.eval(_LIBERA_SE_MEU, 1, _chave_lock(conversa_id), token)  # type: ignore[misc]
