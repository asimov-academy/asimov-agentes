"""O que o agente nativo "manda" fica no Redis por conversa, para o terminal ler.

O turno roda no worker e o terminal chama a API: o Redis é o que os dois enxergam. As mensagens
também vão para o banco no fim do turno, mas lá só aparecem depois do commit; aqui aparecem na hora,
com o digitando entre uma e outra.
"""

import json
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from redis.asyncio import Redis

from app.plataforma.config import config

DURACAO_SAIDA_SEGUNDOS = 7 * 24 * 3600
# O turno desliga o digitando ao terminar; o prazo só cobre worker que caiu no meio.
DURACAO_DIGITANDO_SEGUNDOS = 300


def _saida(conversa: str) -> str:
    return f"nativo:saida:{conversa}"


def _digitando(conversa: str) -> str:
    return f"nativo:digitando:{conversa}"


def _humano(conversa: str) -> str:
    return f"nativo:humano:{conversa}"


@asynccontextmanager
async def conexao() -> AsyncIterator[Redis]:
    cliente = Redis.from_url(config().redis_url)
    try:
        yield cliente
    finally:
        await cliente.aclose()


async def guarda_saida(conversa: str, mensagem: dict[str, Any]) -> None:
    async with conexao() as r:
        await r.rpush(_saida(conversa), json.dumps(mensagem, ensure_ascii=False))  # type: ignore[misc]
        await r.expire(_saida(conversa), DURACAO_SAIDA_SEGUNDOS)


async def le_saida(conversa: str, depois: int) -> list[dict[str, Any]]:
    async with conexao() as r:
        itens = await r.lrange(_saida(conversa), depois, -1)  # type: ignore[misc]
    return [json.loads(i) for i in itens]


async def muda_digitando(conversa: str, ligado: bool) -> None:
    async with conexao() as r:
        if ligado:
            await r.set(_digitando(conversa), "1", ex=DURACAO_DIGITANDO_SEGUNDOS)
        else:
            await r.delete(_digitando(conversa))


async def esta_digitando(conversa: str) -> bool:
    async with conexao() as r:
        return bool(await r.exists(_digitando(conversa)))


async def muda_humano(conversa: str, ligado: bool) -> None:
    async with conexao() as r:
        if ligado:
            await r.set(_humano(conversa), "1")
        else:
            await r.delete(_humano(conversa))


async def humano_conduz(conversa: str) -> bool:
    async with conexao() as r:
        return bool(await r.exists(_humano(conversa)))
