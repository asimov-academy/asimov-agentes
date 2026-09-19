"""Vetores dos trechos: um modelo por instalação, com a chave que a instalação já tem.

Por que da instalação e não do agente: a dimensão do vetor é fixa na coluna, e agentes com modelos
diferentes quebrariam a busca (spec/arquitetura.md). A ordem é OpenAI e depois Gemini, que são os
dois provedores com embedding barato entre os quatro que a plataforma fala; quem só tem chave da
Anthropic ou da Groq não tem base de conhecimento, e a mensagem diz isso.

A mesma função gera o vetor dos trechos e o da pergunta do contato: tem de ser o mesmo modelo, ou a
distância não significa nada.
"""

import httpx

from app.conhecimento.modelos import DIMENSAO
from app.ia import chaves
from app.plataforma.config import Config, config

TIMEOUT_SEGUNDOS = 60.0
LOTE = 64
"""Trechos por chamada. Documento grande vira dezenas de chamadas, e não uma que estoura o limite."""

MODELOS = {
    "openai": "text-embedding-3-small",
    "gemini": "gemini-embedding-001",
}
ORDEM = ("openai", "gemini")


class SemEmbeddings(RuntimeError):
    """Mensagem em português, pronta para a tela."""


def provedor(cfg: Config | None = None) -> str | None:
    cfg = cfg or config()
    for nome in ORDEM:
        if chaves.chave_do_provedor(nome, cfg):
            return nome
    return None


def modelo(cfg: Config | None = None) -> str:
    """`provedor:modelo` do que está valendo, ou vazio quando não dá para gerar vetor nenhum."""
    escolhido = provedor(cfg)
    return f"{escolhido}:{MODELOS[escolhido]}" if escolhido else ""


async def gerar(textos: list[str], cfg: Config | None = None, *, modelo_fixo: str | None = None) -> list[list[float]]:
    """Vetores na ordem dos textos. Levanta `SemEmbeddings` com o que o operador precisa fazer."""
    if not textos:
        return []
    cfg = cfg or config()
    escolhido = modelo_fixo.split(":", 1)[0] if modelo_fixo else provedor(cfg)
    if modelo_fixo and modelo_fixo != f"{escolhido}:{MODELOS.get(escolhido)}":
        raise SemEmbeddings("modelo de embeddings da base não é suportado nesta versão")
    if escolhido is None:
        raise SemEmbeddings(
            "a base de conhecimento precisa da chave da OpenAI ou do Gemini nesta instalação"
        )
    chave = chaves.chave_do_provedor(escolhido, cfg)
    if not chave:
        raise SemEmbeddings(f"a base usa {escolhido}; cadastre a chave desse provedor")
    saida: list[list[float]] = []
    async with httpx.AsyncClient(timeout=TIMEOUT_SEGUNDOS) as http:
        for inicio in range(0, len(textos), LOTE):
            lote = textos[inicio : inicio + LOTE]
            if escolhido == "openai":
                saida += await _openai(http, chave, lote)
            else:
                saida += await _gemini(http, chave, lote)
    return saida


async def _openai(http: httpx.AsyncClient, chave: str, lote: list[str]) -> list[list[float]]:
    resposta = await http.post(
        "https://api.openai.com/v1/embeddings",
        headers={"Authorization": f"Bearer {chave}"},
        json={"model": MODELOS["openai"], "input": lote, "dimensions": DIMENSAO},
    )
    _confere(resposta)
    dados = sorted(resposta.json()["data"], key=lambda d: d["index"])
    return [d["embedding"] for d in dados]


async def _gemini(http: httpx.AsyncClient, chave: str, lote: list[str]) -> list[list[float]]:
    nome = MODELOS["gemini"]
    resposta = await http.post(
        f"https://generativelanguage.googleapis.com/v1beta/models/{nome}:batchEmbedContents",
        headers={"x-goog-api-key": chave},
        json={
            "requests": [
                {
                    "model": f"models/{nome}",
                    "content": {"parts": [{"text": texto}]},
                    "outputDimensionality": DIMENSAO,
                }
                for texto in lote
            ]
        },
    )
    _confere(resposta)
    return [item["values"] for item in resposta.json()["embeddings"]]


def _confere(resposta: httpx.Response) -> None:
    if resposta.status_code == 401 or resposta.status_code == 403:
        raise SemEmbeddings("a chave do provedor de embeddings foi recusada")
    if resposta.status_code >= 400:
        raise SemEmbeddings(f"o provedor de embeddings recusou o pedido ({resposta.status_code})")
