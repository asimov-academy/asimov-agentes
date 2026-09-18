"""Conversa do copiloto no Redis: mensagens, estado do turno e propostas de mudança.

No Redis e não no banco pelo mesmo motivo da sessão do painel: expira sozinha e não deixa lixo
para limpar. Uma conversa de copiloto é descartável, o que ela muda é que fica guardado.

A sessão é uma só por operador (a instalação tem uma conta), então a chave é fixa. Quem abre o
popup de novo continua de onde parou enquanto a sessão durar.
"""

import json
import uuid
from datetime import UTC, datetime
from typing import Any

from app.painel.servico import conexao

CHAVE = "copiloto:sessao"
DURACAO_SEGUNDOS = 12 * 3600
LIMITE_MENSAGENS = 60
"""Teto do que volta ao painel. O fio da conversa de verdade é o do CLI, que guarda o histórico."""


def _agora() -> str:
    return datetime.now(UTC).isoformat()


def nova() -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()),
        "criada_em": _agora(),
        "estado": "parado",
        "mensagens": [],
        "propostas": [],
        # Id da conversa do lado do CLI, para o próximo turno continuar o mesmo fio.
        "conversa_cli": "",
        "erro": "",
    }


async def ler() -> dict[str, Any]:
    async with conexao() as redis:
        cru = await redis.get(CHAVE)
    return json.loads(cru) if cru else nova()


async def grava(sessao: dict[str, Any]) -> dict[str, Any]:
    sessao["mensagens"] = sessao["mensagens"][-LIMITE_MENSAGENS:]
    async with conexao() as redis:
        await redis.set(CHAVE, json.dumps(sessao), ex=DURACAO_SEGUNDOS)
    return sessao


async def limpa() -> None:
    async with conexao() as redis:
        await redis.delete(CHAVE)


async def muda(**campos: Any) -> dict[str, Any]:
    sessao = await ler()
    sessao.update(campos)
    return await grava(sessao)


async def anota_mensagem(autor: str, texto: str) -> dict[str, Any]:
    sessao = await ler()
    sessao["mensagens"].append({"autor": autor, "texto": texto, "em": _agora()})
    return await grava(sessao)


async def anota_proposta(proposta: dict[str, Any]) -> dict[str, Any]:
    """Chamada pelo processo do MCP, que roda fora da API: por isso passa pelo Redis e não por
    memória compartilhada."""
    sessao = await ler()
    proposta = {**proposta, "id": str(uuid.uuid4()), "situacao": "aguardando", "em": _agora()}
    sessao["propostas"].append(proposta)
    await grava(sessao)
    return proposta


async def proposta(proposta_id: str) -> dict[str, Any] | None:
    sessao = await ler()
    return next((p for p in sessao["propostas"] if p["id"] == proposta_id), None)


async def fecha_proposta(proposta_id: str, situacao: str, resultado: str = "") -> dict[str, Any]:
    sessao = await ler()
    for p in sessao["propostas"]:
        if p["id"] == proposta_id:
            p["situacao"] = situacao
            p["resultado"] = resultado
    return await grava(sessao)


def para_o_painel(sessao: dict[str, Any]) -> dict[str, Any]:
    """O que a tela precisa. Proposta já resolvida sai da lista de pendentes, mas fica na conversa."""
    return {
        "id": sessao["id"],
        "estado": sessao["estado"],
        "erro": sessao.get("erro", ""),
        "mensagens": sessao["mensagens"],
        "propostas": sessao["propostas"],
    }
