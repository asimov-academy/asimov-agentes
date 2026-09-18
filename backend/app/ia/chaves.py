"""Chaves de API dos provedores de IA: guardadas cifradas no banco, valem na hora.

O modelo é escolha de cada agente, feita ao criá-lo no terminal ou no painel, e a chave do provedor
é pedida ali, uma vez por instalação. Como a API e o worker são processos separados, cada um guarda
uma cópia em memória e a renova com `carregar` antes de validar modelo ou rodar um turno. Chave que
veio no `.env` de uma instalação antiga continua valendo quando não há outra no banco.
"""

import re
from typing import Any

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.acessos import repo
from app.ia.provedores import PROVEDORES, PROVEDORES_TRANSCRICAO, ModeloInvalido
from app.plataforma.config import Config, config

FUNCOES = ("conversa", "auxiliar", "visao", "transcricao")

_guardadas: dict[str, str] = {}


class ChaveRecusada(ValueError):
    """Mensagem em português, pronta para a tela."""


def chave_do_provedor(provedor: str, cfg: Config | None = None) -> str:
    return _guardadas.get(provedor) or (cfg or config()).chave_do_provedor(provedor)


async def carregar(sessao: AsyncSession) -> None:
    guardadas = await repo.chaves_de_provedor(sessao)
    _guardadas.clear()
    _guardadas.update(guardadas)


async def provedores_com_chave(sessao: AsyncSession) -> list[str]:
    await carregar(sessao)
    return [p for p in PROVEDORES if chave_do_provedor(p)]


def _confere_provedor(provedor: str) -> None:
    if provedor not in PROVEDORES:
        raise ModeloInvalido(f"provedor {provedor!r} desconhecido; use {', '.join(PROVEDORES)}")


async def _consulta(provedor: str, chave: str) -> httpx.Response:
    """Lista de modelos do provedor: serve de teste da chave e de catálogo."""
    if provedor == "anthropic":
        url = "https://api.anthropic.com/v1/models?limit=100"
        cabecalhos = {"x-api-key": chave, "anthropic-version": "2023-06-01"}
    elif provedor == "gemini":
        url = "https://generativelanguage.googleapis.com/v1beta/models?pageSize=1000"
        cabecalhos = {"x-goog-api-key": chave}
    else:
        base = "https://api.openai.com/v1" if provedor == "openai" else "https://api.groq.com/openai/v1"
        url = f"{base}/models"
        cabecalhos = {"Authorization": f"Bearer {chave}"}
    async with httpx.AsyncClient(timeout=20) as http:
        return await http.get(url, headers=cabecalhos)


async def guardar(sessao: AsyncSession, provedor: str, chave: str) -> None:
    """Testa no provedor e só então guarda. Quem chama não faz commit: sai daqui gravado."""
    _confere_provedor(provedor)
    chave = chave.strip()
    if not chave:
        raise ChaveRecusada("chave vazia")
    try:
        resposta = await _consulta(provedor, chave)
    except httpx.HTTPError as erro:
        raise ChaveRecusada(f"não consegui falar com {provedor} para testar a chave") from erro
    if resposta.status_code != 200:
        raise ChaveRecusada("chave recusada: confira se copiou inteira e se a conta tem crédito")
    await repo.guardar_chave_de_provedor(sessao, provedor, chave)
    await sessao.commit()
    _guardadas[provedor] = chave


async def esquecer(sessao: AsyncSession, provedor: str) -> bool:
    _confere_provedor(provedor)
    apagada = await repo.apagar_chave_de_provedor(sessao, provedor)
    await sessao.commit()
    _guardadas.pop(provedor, None)
    return apagada


# Sugestões aparecem primeiro, mas só se o provedor ainda listar o modelo. São os padrões de `ia/`:
# nome de modelo não aparece em nenhum outro lugar do código.
PREFERIDOS: dict[tuple[str, str], tuple[str, ...]] = {
    ("openai", "conversa"): ("gpt-5.5", "gpt-5.1", "gpt-5", "gpt-4.1"),
    ("openai", "visao"): ("gpt-5-mini", "gpt-5.1", "gpt-4.1-mini"),
    ("openai", "transcricao"): ("gpt-4o-transcribe", "whisper-1", "gpt-4o-mini-transcribe"),
    ("openai", "auxiliar"): ("gpt-5-mini", "gpt-5-nano", "gpt-4.1-mini"),
    ("anthropic", "conversa"): ("claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5"),
    ("anthropic", "visao"): ("claude-sonnet-5", "claude-opus-5", "claude-haiku-4-5"),
    ("anthropic", "auxiliar"): ("claude-haiku-4-5", "claude-sonnet-5"),
    ("gemini", "conversa"): ("gemini-2.5-pro", "gemini-2.5-flash"),
    ("gemini", "visao"): ("gemini-2.5-flash", "gemini-2.5-pro"),
    ("gemini", "transcricao"): ("gemini-2.5-flash", "gemini-2.5-pro"),
    ("gemini", "auxiliar"): ("gemini-2.5-flash", "gemini-2.5-pro"),
    ("groq", "conversa"): ("llama-3.3-70b-versatile", "openai/gpt-oss-120b", "moonshotai/kimi-k2-instruct"),
    ("groq", "visao"): ("meta-llama/llama-4-scout-17b-16e-instruct", "meta-llama/llama-4-maverick-17b-128e-instruct"),
    ("groq", "transcricao"): ("whisper-large-v3-turbo", "whisper-large-v3"),
    ("groq", "auxiliar"): ("llama-3.1-8b-instant", "llama-3.3-70b-versatile", "openai/gpt-oss-20b"),
}

_SO_AUDIO = re.compile(r"whisper|transcribe")
_NAO_CONVERSA = re.compile(
    r"whisper|transcribe|tts|audio|realtime|embed|image|dall-e|moderation|guard|search|babbage|"
    r"davinci|sora|codex|computer|preview|exp"
)
_OPENAI_DE_TEXTO = re.compile(r"^(gpt-|o[0-9])")
LIMITE_DA_LISTA = 8


def filtra(provedor: str, funcao: str, ids: list[str]) -> list[str]:
    """Só o que serve para a função, sugeridos primeiro, até oito."""
    if funcao == "transcricao" and provedor != "gemini":
        servem = [i for i in ids if _SO_AUDIO.search(i)]
    else:
        servem = [i for i in ids if not _NAO_CONVERSA.search(i)]
        if provedor == "openai":
            servem = [i for i in servem if _OPENAI_DE_TEXTO.search(i)]
    primeiro = [p for p in PREFERIDOS.get((provedor, funcao), ()) if p in servem]
    resto = sorted((i for i in servem if i not in primeiro), reverse=True)
    return (primeiro + resto)[:LIMITE_DA_LISTA]


def _ids(provedor: str, corpo: dict[str, Any]) -> list[str]:
    if provedor == "gemini":
        return [
            str(m.get("name", "")).removeprefix("models/")
            for m in corpo.get("models") or []
            if "generateContent" in (m.get("supportedGenerationMethods") or [])
            and str(m.get("name", "")).startswith("models/gemini")
        ]
    return [str(m.get("id")) for m in corpo.get("data") or [] if m.get("id")]


async def listar_modelos(sessao: AsyncSession, provedor: str, funcao: str) -> list[str]:
    """Modelos do provedor para a função, já no formato `provedor:modelo`.

    Provedor fora do ar devolve só as sugestões: a tela deixa digitar outro, e quem valida o
    formato e a chave é o backend na hora de gravar.
    """
    _confere_provedor(provedor)
    if funcao not in FUNCOES:
        raise ModeloInvalido(f"função {funcao!r} desconhecida; use {', '.join(FUNCOES)}")
    if funcao == "transcricao" and provedor not in PROVEDORES_TRANSCRICAO:
        raise ModeloInvalido(f"{provedor} não transcreve áudio; use openai, gemini ou groq")
    await carregar(sessao)
    chave = chave_do_provedor(provedor)
    if not chave:
        raise ModeloInvalido(f"a instalação não tem a chave de {provedor}")
    try:
        resposta = await _consulta(provedor, chave)
        resposta.raise_for_status()
        modelos = filtra(provedor, funcao, _ids(provedor, resposta.json()))
    except (httpx.HTTPError, ValueError):
        modelos = list(PREFERIDOS.get((provedor, funcao), ()))
    return [f"{provedor}:{m}" for m in modelos]


def completa(modelos: dict[str, str | None], cfg: Config | None = None) -> dict[str, str | None]:
    """Preenche o que o operador não escolheu a partir do modelo de resposta.

    Resumo, visão e áudio nascem no mesmo provedor da resposta, com a primeira sugestão de cada
    função; áudio cai em outro provedor com chave quando o da resposta não transcreve (Anthropic).
    Padrão do `.env` de instalação antiga vem antes disso.

    Sem modelo de resposta escolhido, o agente nasce com a IA que a instalação já tem: escolher
    provedor e modelo deixou de ser pergunta da criação no painel (o operador não tem como decidir
    isso antes de ver o agente falar) e virou item da ficha, onde ele troca depois.
    """
    from app.ia.provedores import provedor_de

    cfg = cfg or config()
    final: dict[str, str | None] = {
        "modelo_conversa": cfg.modelo_conversa or None,
        "modelo_fallback": cfg.modelo_fallback or None,
        "modelo_auxiliar": None,
        "modelo_visao": cfg.modelo_visao or None,
        "modelo_transcricao": cfg.modelo_transcricao or None,
        **{c: v for c, v in modelos.items() if v},
    }
    conversa = final["modelo_conversa"] = final["modelo_conversa"] or _primeiro_com_chave(cfg)
    if not conversa:
        raise ModeloInvalido(
            "nenhuma chave de IA guardada nesta instalação: guarde a chave de um provedor antes de criar o agente"
        )
    provedor = provedor_de(conversa)
    # Instalação antiga: o resumo sempre foi o modelo de resposta. Só a nova sugere um mais barato.
    if not final["modelo_auxiliar"]:
        final["modelo_auxiliar"] = conversa if cfg.modelo_conversa else _sugestao(provedor, "auxiliar") or conversa
    if not final["modelo_visao"]:
        final["modelo_visao"] = _sugestao(provedor, "visao") or conversa
    if not final["modelo_transcricao"]:
        candidatos = [provedor, *[p for p in PROVEDORES_TRANSCRICAO if p != provedor]]
        for candidato in candidatos:
            if candidato in PROVEDORES_TRANSCRICAO and chave_do_provedor(candidato, cfg):
                final["modelo_transcricao"] = _sugestao(candidato, "transcricao")
                break
    return final


def _primeiro_com_chave(cfg: Config) -> str | None:
    """Modelo de resposta do primeiro provedor com chave, na ordem de `PROVEDORES`."""
    for provedor in PROVEDORES:
        if chave_do_provedor(provedor, cfg):
            return _sugestao(provedor, "conversa")
    return None


def _sugestao(provedor: str, funcao: str) -> str | None:
    preferidos = PREFERIDOS.get((provedor, funcao))
    return f"{provedor}:{preferidos[0]}" if preferidos else None
