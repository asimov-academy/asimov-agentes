import uuid
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from app.canais.waha import vigia
from app.conversas.turno import processar_turno
from app.handoff import servico as handoff
from app.plataforma.banco import fabrica_sessao
from app.plataforma.config import config
from app.plataforma.log import configura_log


async def ao_iniciar(ctx: dict[str, Any]) -> None:
    configura_log(config().log_nivel)


async def assumir_conversa(
    ctx: dict[str, Any], cliente_id: str, conversa_id: str, autor_externo: str | None = None
) -> bool:
    """Uma pessoa da equipe assumiu a conversa: o canal mostra isso (no Chatwoot, aberta e atribuída)."""
    async with fabrica_sessao()() as s:
        return await handoff.assumir_no_canal(s, uuid.UUID(cliente_id), uuid.UUID(conversa_id), autor_externo)


async def retomada_automatica(ctx: dict[str, Any]) -> int:
    """De minuto em minuto: conversa cujo prazo de handoff venceu volta para o agente."""
    async with fabrica_sessao()() as s:
        return await handoff.retomada_automatica(s)


async def confere_whatsapp(ctx: dict[str, Any]) -> int:
    """De dez em dez minutos: número desconectado do WhatsApp deixa o agente mudo, e isso precisa
    aparecer em Ver consumo e falhas mesmo quando o evento da WAHA não chega."""
    async with fabrica_sessao()() as s:
        return await vigia.confere_sessoes(s, ctx["redis"])


class Configuracao:
    functions = [processar_turno, assumir_conversa]
    cron_jobs = [
        cron(retomada_automatica, second=0, run_at_startup=False),
        cron(confere_whatsapp, minute={0, 10, 20, 30, 40, 50}, second=30, run_at_startup=False),
    ]
    on_startup = ao_iniciar
    redis_settings = RedisSettings.from_dsn(config().redis_url)
    max_jobs = 20
    job_timeout = 300
