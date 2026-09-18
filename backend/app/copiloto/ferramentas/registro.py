"""Catálogo das ferramentas do copiloto, na ordem em que o modelo as vê.

Ferramenta nova: um arquivo nesta pasta com `FERRAMENTA` (ficha em `base.py`) e uma linha em
FICHAS. Um teste recusa arquivo desta pasta que não esteja no registro, como no catálogo das
ferramentas do agente.
"""

from app.copiloto.ferramentas import (
    listar_agentes,
    listar_empresas,
    listar_ferramentas,
    propor_agente_novo,
    propor_mudanca_no_agente,
    ver_agente,
)
from app.copiloto.ferramentas.base import FerramentaDoCopiloto

FICHAS: tuple[FerramentaDoCopiloto, ...] = (
    listar_empresas.FERRAMENTA,
    listar_agentes.FERRAMENTA,
    ver_agente.FERRAMENTA,
    listar_ferramentas.FERRAMENTA,
    propor_mudanca_no_agente.FERRAMENTA,
    propor_agente_novo.FERRAMENTA,
)
CATALOGO: dict[str, FerramentaDoCopiloto] = {f.nome: f for f in FICHAS}
