"""Buffer e lock por conversa, no Redis.

Buffer: cada mensagem do contato grava um token novo e agenda o turno para daqui a
`buffer_segundos`. Quando o job acorda, só segue se o token ainda for o último; mensagem
nova durante a espera invalida o job anterior. O contato manda cinco mensagens e recebe
uma resposta.

**Token que venceu não é mensagem nova.** O prazo do token é operacional (limpar chave velha do
Redis); quem invalida um turno é outra mensagem, que grava um token diferente. Antes da auditoria
de 2026-09-18 as duas coisas eram a mesma, e uma fila lenta ou um modelo demorado faziam a resposta
ser descartada em silêncio, sem ninguém para refazê-la (A03).

Lock: impede dois turnos simultâneos na mesma conversa. A liberação confere o token antes
de apagar, para um job lento não derrubar o lock de outro, e `lock_e_meu` deixa o turno conferir a
posse antes de cada efeito externo, caso o prazo tenha vencido com ele ainda vivo (A06).
"""

import uuid
from typing import Any

from redis.asyncio import Redis

from app.plataforma.config import config

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


def prazo_do_token(buffer_segundos: int) -> int:
    """Cobre a espera do buffer, a fila, a mídia, o modelo e o envio, com folga.

    Não é o que decide se o turno vale: é só quanto tempo a chave fica no Redis.
    """
    return buffer_segundos + config().lock_ttl_segundos + 300


async def agenda_turno(
    fila: Any, cliente_id: uuid.UUID, conversa_id: uuid.UUID, buffer_segundos: int
) -> str:
    token = uuid.uuid4().hex
    await fila.set(_chave_buffer(conversa_id), token, ex=prazo_do_token(buffer_segundos))
    await fila.enqueue_job(
        "processar_turno", str(cliente_id), str(conversa_id), token, _defer_by=buffer_segundos
    )
    return token


async def nao_foi_substituido(redis: Redis, conversa_id: uuid.UUID, token: str) -> bool:
    """Falso só quando existe um token diferente, que é mensagem nova esperando resposta.

    Chave ausente é prazo vencido, não substituição: descartar aí perderia a resposta sem nada
    para refazê-la.
    """
    atual = await redis.get(_chave_buffer(conversa_id))
    if isinstance(atual, bytes):
        atual = atual.decode()
    return atual is None or atual == token


async def ja_agendado(redis: Redis, conversa_id: uuid.UUID) -> bool:
    """Existe token de buffer para esta conversa, ou seja, algum turno foi agendado.

    Some quando o agendamento nunca aconteceu (Redis fora do ar na hora do webhook) ou quando o
    prazo venceu sem ninguém responder. Nos dois casos, uma reentrega do canal pode recuperar o
    turno perdido sem duplicar o de quem já está agendado (A01).
    """
    return bool(await redis.exists(_chave_buffer(conversa_id)))


async def adquire_lock(redis: Redis, conversa_id: uuid.UUID, token: str, ttl: int) -> bool:
    return bool(await redis.set(_chave_lock(conversa_id), token, nx=True, ex=ttl))


async def turno_em_andamento(redis: Redis, conversa_id: uuid.UUID) -> bool:
    return bool(await redis.exists(_chave_lock(conversa_id)))


async def lock_e_meu(redis: Redis, conversa_id: uuid.UUID, token: str) -> bool:
    """O lock ainda é deste turno. Prazo vencido com outro turno dentro devolve falso."""
    atual = await redis.get(_chave_lock(conversa_id))
    if isinstance(atual, bytes):
        atual = atual.decode()
    return atual == token


async def libera_lock(redis: Redis, conversa_id: uuid.UUID, token: str) -> None:
    await redis.eval(_LIBERA_SE_MEU, 1, _chave_lock(conversa_id), token)  # type: ignore[misc]
