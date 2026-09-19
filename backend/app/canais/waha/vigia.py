"""Confere de tempos em tempos se os números dos agentes continuam no ar.

O WhatsApp derruba o aparelho sem avisar (o número entrou em outro celular, ficou muito tempo
offline, o dono desconectou na mão). Quando isso acontece, a WAHA deixa de entregar mensagens e o
agente fica mudo sem ninguém saber. O evento `session.status` do webhook cobre a maior parte dos
casos; esta ronda é a rede de segurança para quando nem o evento chega (contêiner reiniciado, WAHA
fora do ar).

Uma falha por agente a cada hora: o operador precisa saber, não ser inundado.
"""

from typing import Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.canais.base import CredencialInvalida
from app.canais.waha import api
from app.consumo.repo import registra_falha

log = structlog.get_logger()

ESPERA_ENTRE_AVISOS_SEGUNDOS = 3600
JANELA_DE_PAREAMENTO_SEGUNDOS = 900
"""Depois de pedir um QR code novo, a sessão passa por STOPPED antes de voltar: alarme aí seria
sobre o que o próprio operador acabou de fazer."""


def chave_de_pareamento(agente_id: Any) -> str:
    return f"waha:pareando:{agente_id}"


async def marca_pareamento(redis: Any, agente_id: Any) -> None:
    try:
        await redis.set(chave_de_pareamento(agente_id), "1", ex=JANELA_DE_PAREAMENTO_SEGUNDOS)
    except Exception as erro:
        log.warning("marca_pareamento_falhou", erro=repr(erro))


async def pareando_agora(redis: Any, agente_id: Any) -> bool:
    if redis is None:
        return False
    try:
        return await redis.get(chave_de_pareamento(agente_id)) is not None
    except Exception:
        return False
STATUS_QUE_ATENDEM = ("WORKING",)
STATUS_PASSAGEIROS = ("STARTING", "SCAN_QR_CODE")
"""Pareamento em andamento não é problema: alguém está com o QR code na tela."""


async def confere_sessoes(sessao: AsyncSession, redis: Any) -> int:
    """Devolve quantos agentes estão com o número fora do ar agora."""
    fora = 0
    for agente in await agentes_repo.listar_de_todos_os_clientes(sessao):
        if agente.canal != "waha" or agente.desligado:
            continue
        nome = agentes_servico.credenciais(agente).get("sessao")
        if not nome:
            continue
        try:
            status = str((await api.situacao(str(nome))).get("status"))
        except CredencialInvalida as erro:
            status = f"WAHA sem resposta ({erro})"
        if status in STATUS_QUE_ATENDEM or status in STATUS_PASSAGEIROS:
            continue
        if await pareando_agora(redis, agente.id):
            continue
        fora += 1
        if await _pode_avisar(redis, agente.id, status):
            await registra_falha(
                "canal_fora_do_ar",
                {"canal": "waha", "situacao": status, "motivo": "o número saiu do ar no WhatsApp"},
                agente.cliente_id,
                agente.id,
            )
            log.error("canal_fora_do_ar", agente_id=str(agente.id), situacao=status)
    return fora


async def _pode_avisar(redis: Any, agente_id: Any, status: str) -> bool:
    """Uma falha por agente por hora. Redis fora do ar não silencia o aviso."""
    try:
        return bool(await redis.set(f"waha:aviso:{agente_id}", status, ex=ESPERA_ENTRE_AVISOS_SEGUNDOS, nx=True))
    except Exception:
        return True
