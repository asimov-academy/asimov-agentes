"""Catálogo das ferramentas que o operador liga e desliga por agente (`Agente.ferramentas`).

Ferramenta nova: um arquivo nesta pasta com `FERRAMENTA` (ficha em `base.py`) e uma linha em FICHAS. A ordem de
FICHAS é a do menu. `transferir_para_humano` não está aqui: todo agente tem (`handoff/tool.py`).
"""

from typing import Any

from app.ia.ferramentas import busca_web, calculadora
from app.ia.ferramentas.base import Ferramenta

FICHAS: tuple[Ferramenta, ...] = (
    calculadora.FERRAMENTA,
    busca_web.FERRAMENTA,
)
CATALOGO: dict[str, Ferramenta] = {ficha.nome: ficha for ficha in FICHAS}
PADRAO = [ficha.nome for ficha in FICHAS if ficha.padrao]


class FerramentaDesconhecida(ValueError):
    pass


def valida(nomes: list[str]) -> list[str]:
    desconhecidas = sorted(set(nomes) - set(CATALOGO))
    if desconhecidas:
        raise FerramentaDesconhecida(f"ferramentas que não existem: {', '.join(desconhecidas)}")
    return [n for n in CATALOGO if n in nomes]


def monta(nomes: list[str] | None) -> tuple[list[Any], list[Any], list[str]]:
    """Tools, capabilities e instruções do agente. Nome que saiu do catálogo é ignorado, sem derrubar o turno."""
    tools: list[Any] = []
    capabilities: list[Any] = []
    instrucoes: list[str] = []
    for nome in nomes or []:
        ferramenta = CATALOGO.get(nome)
        if ferramenta is not None:
            tools += ferramenta.tools()
            capabilities += ferramenta.capabilities()
            instrucoes.append(ferramenta.instrucao)
    return tools, capabilities, instrucoes
