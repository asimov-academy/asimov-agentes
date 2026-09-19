"""Divisão do texto em trechos: o que a busca devolve e o que entra na resposta do agente.

Cerca de 800 tokens por trecho, com 100 de sobreposição (spec/arquitetura.md). Em português, um
token dá mais ou menos quatro caracteres, e o corte respeita parágrafo e frase: trecho que começa
no meio de uma frase responde pior e lê pior no painel.
"""

import re

CARACTERES_POR_TOKEN = 4
TAMANHO = 800 * CARACTERES_POR_TOKEN
SOBREPOSICAO = 100 * CARACTERES_POR_TOKEN
MINIMO = 120
"""Sobra menor que isto vira cauda do trecho anterior, em vez de trecho quase vazio."""

_FIM_DE_FRASE = re.compile(r"[.!?]\s")


def _corte(texto: str, fim: int) -> int:
    """Onde cortar perto de `fim`: fim de parágrafo, senão fim de frase, senão o próprio `fim`."""
    janela = texto[:fim]
    paragrafo = janela.rfind("\n\n")
    if paragrafo > fim * 0.5:
        return paragrafo + 2
    frases = list(_FIM_DE_FRASE.finditer(janela))
    if frases and frases[-1].end() > fim * 0.5:
        return frases[-1].end()
    espaco = janela.rfind(" ")
    return espaco + 1 if espaco > fim * 0.5 else fim


def em_trechos(texto: str, tamanho: int = TAMANHO, sobreposicao: int = SOBREPOSICAO) -> list[str]:
    texto = texto.strip()
    if not texto:
        return []
    trechos: list[str] = []
    inicio = 0
    while inicio < len(texto):
        if len(texto) - inicio <= tamanho:
            trechos.append(texto[inicio:].strip())
            break
        fim = inicio + _corte(texto[inicio:], tamanho)
        trechos.append(texto[inicio:fim].strip())
        proximo = max(fim - sobreposicao, inicio + 1)
        if len(texto) - proximo < MINIMO:
            break
        inicio = proximo
    return [t for t in trechos if t]
