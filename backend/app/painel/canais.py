"""A situação do canal de cada agente, para a tela de Canais do painel.

Cada canal responde a mesma pergunta com o que ele sabe: o WhatsApp pelo aparelho pergunta à WAHA
se a sessão está pareada, o oficial pergunta à Meta se o número segue de pé, o Chatwoot mostra a
caixa em que o bot foi ligado e o nativo não tem nada para perguntar.

Nenhuma regra nova nasce aqui: é a mesma consulta que o menu do terminal faz, com o resultado no
formato que a tela precisa. Consulta que falha vira situação `desconhecida` com o motivo, e nunca
derruba a tela inteira: um canal fora do ar não pode esconder os outros.
"""

from typing import Any

import structlog

from app.agentes import servico as agentes_servico
from app.agentes.modelos import Agente
from app.canais.base import CredencialInvalida
from app.canais.waha import api as waha_api
from app.canais.whatsapp import api as whatsapp_api

log = structlog.get_logger()


async def situacao(agente: Agente) -> dict[str, Any]:
    """`cor`, `resumo` e o que cada canal tem de específico. Sem exceção para fora."""
    try:
        if agente.canal == "waha":
            return await _waha(agente)
        if agente.canal == "whatsapp":
            return await _whatsapp(agente)
        if agente.canal == "chatwoot":
            return _chatwoot(agente)
        return {"cor": "neutro", "resumo": "Sem canal externo: só a conversa de teste."}
    except CredencialInvalida as erro:
        log.warning("canal_nao_respondeu", agente_id=str(agente.id), canal=agente.canal)
        return {"cor": "perigo", "resumo": "O canal não respondeu agora.", "erro": str(erro)}
    except Exception as erro:  # noqa: BLE001 - a tela mostra os outros canais mesmo assim
        log.error("canal_erro_inesperado", agente_id=str(agente.id), erro=repr(erro))
        return {"cor": "perigo", "resumo": "Não consegui conferir este canal."}


def _nome_da_sessao(agente: Agente) -> str:
    return str(agentes_servico.credenciais(agente).get("sessao") or agente.slug)


async def _waha(agente: Agente) -> dict[str, Any]:
    dados = await waha_api.situacao(_nome_da_sessao(agente))
    status = str(dados.get("status"))
    eu: dict[str, Any] = dados.get("me") or {}
    numero = str(eu.get("id") or "").split("@")[0] or None
    pareado = status == waha_api.STATUS_PAREADO
    return {
        "cor": "ok" if pareado else "atencao" if status == waha_api.STATUS_QR else "perigo",
        "resumo": (
            f"Número {numero} conectado."
            if pareado
            else "Esperando a leitura do QR code."
            if status == waha_api.STATUS_QR
            else f"A sessão está em {status}."
        ),
        "status": status,
        "pareado": pareado,
        "numero": numero,
        "nome": eu.get("pushName"),
        "pode_reiniciar": True,
    }


async def _whatsapp(agente: Agente) -> dict[str, Any]:
    credenciais = agentes_servico.credenciais(agente)
    ficha = await whatsapp_api.numero(credenciais["access_token"], credenciais["phone_number_id"])
    return {
        "cor": "ok",
        "resumo": f"Número {ficha['numero']} respondendo na Meta.",
        "numero": ficha["numero"],
        "nome": ficha["nome"],
        "pode_refazer_webhook": True,
    }


def _chatwoot(agente: Agente) -> dict[str, Any]:
    credenciais = agentes_servico.credenciais(agente)
    caixas = credenciais.get("inbox_ids") or []
    return {
        "cor": "ok",
        "resumo": f"Bot ligado em {len(caixas)} {'caixa' if len(caixas) == 1 else 'caixas'}.",
        "url": credenciais.get("url"),
        "caixas": caixas,
    }


async def reinicia(agente: Agente) -> dict[str, Any]:
    """Para e inicia a sessão da WAHA, para vir um QR code novo. Só faz sentido nesse canal."""
    nome = _nome_da_sessao(agente)
    await waha_api.para_sessao(nome)
    await waha_api.inicia_sessao(nome)
    return await _waha(agente)


async def qr_code(agente: Agente) -> str | None:
    """O QR code como PNG em base64, para o navegador desenhar.

    O terminal usa o texto cru com o `qrencode`; aqui quem desenha é a própria WAHA. Fora do estado
    de leitura não existe QR, e a resposta é nula em vez de erro: a tela pergunta em laço enquanto o
    operador lê.
    """
    nome = _nome_da_sessao(agente)
    dados = await waha_api.situacao(nome)
    if dados.get("status") != waha_api.STATUS_QR:
        return None
    return await waha_api.qr_code_imagem(nome)
