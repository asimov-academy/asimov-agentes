"""Acesso do operador ao canal: pedido uma vez, guardado cifrado e reaproveitado.

Quem precisa do acesso (descobrir, criar agente, renomear, remover) chama `usa_acesso` com o que o
operador informou agora, se informou. Sem acesso informado nem guardado, ou com o canal recusando,
levanta AcessoNecessario: o menu pede o token e tenta de novo. Acesso informado que funcionou fica
guardado; guardado que o canal recusou é apagado.
"""

from collections.abc import Awaitable, Callable
from typing import Any, TypeVar

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.acessos import repo
from app.canais.base import AcessoRecusado, Canal

log = structlog.get_logger()
T = TypeVar("T")


class AcessoNecessario(LookupError):
    """Mensagem em português, pronta para o menu mostrar antes de pedir o token."""


async def usa_acesso(
    sessao: AsyncSession,
    canal: Canal,
    endereco: str,
    informado: dict[str, Any] | None,
    operacao: Callable[[dict[str, Any]], Awaitable[T]],
) -> T:
    """Roda `operacao` com o acesso. Quem chama faz o commit (o acesso guardado vai junto)."""
    acesso = canal.acesso_do_operador(informado or {})
    guardado = False
    if not acesso:
        acesso = await repo.obter(sessao, canal.nome, endereco)
        guardado = True
    if not acesso:
        raise AcessoNecessario(f"informe o token de administrador do {canal.nome} em {endereco}")
    try:
        resultado = await operacao(acesso)
    except AcessoRecusado as erro:
        if guardado:
            await repo.apagar(sessao, canal.nome, endereco)
            await sessao.commit()
            log.info("acesso_guardado_recusado", canal=canal.nome)
        raise AcessoNecessario(f"{erro}; informe outro token") from erro
    if not guardado:
        await repo.guardar(sessao, canal.nome, endereco, acesso)
    return resultado


async def esquecer(sessao: AsyncSession, canal: str, endereco: str) -> bool:
    apagado = await repo.apagar(sessao, canal, endereco)
    await sessao.commit()
    return apagado


async def enderecos(sessao: AsyncSession, canal: str) -> list[dict[str, Any]]:
    """Onde há acesso guardado. O acesso em si nunca sai."""
    return [
        {"endereco": a.endereco, "atualizado_em": a.atualizado_em}
        for a in await repo.listar(sessao, canal)
    ]
