"""Aplica uma proposta do copiloto, depois de o operador confirmar no painel.

Este é o único caminho de escrita do copiloto, e ele é sempre um clique do operador. Nada roda
aqui a partir do modelo: quem chama é a rota `POST /painel/api/copiloto/propostas/{id}`.

As mudanças passam pelos mesmos `servico.py` que o painel e o menu do terminal chamam, com os
mesmos limites e as mesmas validações. O copiloto não ganha atalho nenhum por ser copiloto.
"""

import uuid
from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.clientes import repo as clientes_repo

log = structlog.get_logger()

# Limites iguais aos do painel, para o copiloto não conseguir gravar o que a tela recusa.
LIMITES = {
    "buffer_segundos": (1, 60),
    "max_mensagens_por_resposta": (1, 10),
}


class PropostaInvalida(ValueError):
    """Mensagem em português, pronta para a tela."""


def valida_personalidade(campos: dict[str, Any]) -> None:
    if "tom" in campos and campos["tom"] not in ("formal", "normal", "descontraido"):
        raise PropostaInvalida("tom desconhecido")
    if "ritmo" in campos and campos["ritmo"] not in ("instantaneo", "natural", "reflexivo"):
        raise PropostaInvalida("ritmo desconhecido")
    for nome in ("restringe_temas", "transfere_para_humano", "memoria_ativa", "avisa_que_e_ia"):
        if nome in campos and type(campos[nome]) is not bool:
            raise PropostaInvalida(f"{nome} precisa ser verdadeiro ou falso")


async def aplica(sessao: AsyncSession, proposta: dict[str, Any]) -> str:
    """Devolve uma frase curta dizendo o que foi feito, que volta ao copiloto e à tela."""
    if proposta.get("situacao") != "aguardando":
        raise PropostaInvalida("esta proposta já foi resolvida")
    if proposta["tipo"] == "mudanca":
        return await _muda_agente(sessao, proposta)
    if proposta["tipo"] == "agente_novo":
        return await _cria_agente(sessao, proposta)
    raise PropostaInvalida("proposta de um tipo que não existe")


def _confere_limites(campos: dict[str, Any]) -> None:
    for campo, (minimo, maximo) in LIMITES.items():
        valor = campos.get(campo)
        if valor is not None and not minimo <= int(valor) <= maximo:
            raise PropostaInvalida(f"{campo} precisa ficar entre {minimo} e {maximo}")


async def _muda_agente(sessao: AsyncSession, proposta: dict[str, Any]) -> str:
    cliente_id = uuid.UUID(proposta["cliente_id"])
    agente_id = uuid.UUID(proposta["agente_id"])
    agente = await agentes_repo.obter(sessao, cliente_id, agente_id)
    if agente is None:
        raise PropostaInvalida("o agente da proposta não existe mais")

    campos = dict(proposta.get("campos") or {})
    _confere_limites(campos)
    valida_personalidade(campos)
    if campos:
        agente = await agentes_servico.editar_agente(sessao, cliente_id, agente_id, campos)
    if proposta.get("prompt") is not None:
        agentes_servico.escreve_prompt_do_agente(agente, proposta["prompt"])

    mudou = sorted(campos) + (["prompt"] if proposta.get("prompt") is not None else [])
    log.info("copiloto_aplicou", tipo="mudanca", agente_id=str(agente_id), campos=mudou)
    return f"{agente.nome} atualizado: {', '.join(mudou)}. Vale a partir da próxima mensagem."


async def _cria_agente(sessao: AsyncSession, proposta: dict[str, Any]) -> str:
    cliente_id = uuid.UUID(proposta["cliente_id"])
    cliente = await clientes_repo.obter(sessao, cliente_id)
    if cliente is None:
        raise PropostaInvalida("a empresa da proposta não existe mais")

    agente, _ = await agentes_servico.criar_agente(
        sessao,
        cliente_id,
        nome=proposta["nome"],
        # Nativo é o único canal que o copiloto cria sozinho: os outros pedem credencial de fora.
        canal="nativo",
        conexao={},
        ferramentas=proposta.get("ferramentas") or [],
    )
    if proposta.get("prompt"):
        agentes_servico.escreve_prompt_do_agente(agente, proposta["prompt"])
    log.info("copiloto_aplicou", tipo="agente_novo", agente_id=str(agente.id))
    return (
        f"{agente.nome} criado em {cliente.nome} para conversar no painel e no terminal. "
        "Conectar ao WhatsApp ou ao Chatwoot é o próximo passo, na ficha do agente."
    )
