"""Ficha de uma ferramenta do copiloto: o que o modelo pode chamar pelo MCP.

Uma ferramenta por arquivo desta pasta, exportando `FERRAMENTA`; `registro.py` lista as fichas.
Mesma regra das ferramentas do agente (`ia/ferramentas/`), e um teste confere.

A ficha separa leitura de proposta. Ferramenta que `escreve` não escreve nada: ela registra uma
proposta na sessão do copiloto e devolve ao modelo que o operador ainda precisa confirmar. Quem
aplica é `app/copiloto/aplicar.py`, chamado pela rota que o operador clica.
"""

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class FerramentaDoCopiloto:
    nome: str
    """Estável: é o nome que o modelo vê e o que aparece no log. Igual ao nome do arquivo."""
    descricao: str
    """Uma linha dizendo quando usar. É o que o modelo lê antes de escolher."""
    funcao: Callable[..., Any]
    """Função assíncrona com argumentos tipados e docstring: é dela que sai o schema do MCP."""
    escreve: bool = False
    """Registra proposta em vez de responder. Nenhuma ferramenta muda a plataforma sozinha."""
