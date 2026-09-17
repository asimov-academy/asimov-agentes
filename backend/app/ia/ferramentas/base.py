"""Ficha de uma ferramenta: o que o menu mostra, o que o modelo recebe e se vem ligada no agente novo.

Cada ferramenta mora no próprio arquivo desta pasta e exporta `FERRAMENTA`; `registro.py` lista as fichas.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class Ferramenta:
    nome: str
    """Estável: é o que fica gravado em `Agente.ferramentas`. Igual ao nome do arquivo."""
    rotulo: str
    descricao: str
    """Uma linha para o menu `asimov` > Editar > Ferramentas."""
    instrucao: str
    """Quando usar, no prompt de sistema. Sem ela o modelo pode ter a ferramenta e não usar (v0.8.3)."""
    padrao: bool = False
    """Vem ligada no agente novo."""
    tools: Callable[[], list[Any]] = field(default=lambda: [])
    """Funções que o modelo chama (tools da PydanticAI)."""
    capabilities: Callable[[], list[Any]] = field(default=lambda: [])
    """Capabilities da PydanticAI (ex.: busca nativa do provedor)."""
