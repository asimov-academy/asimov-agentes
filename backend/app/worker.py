import uuid
from typing import Any

from arq import cron
from arq.connections import RedisSettings

from app.canais.waha import vigia
from app.conhecimento import servico as conhecimento
from app.conversas.turno import processar_turno
from app.handoff import servico as handoff
from app.midia import servico as midia
from app.plataforma.banco import fabrica_sessao
from app.plataforma.config import config
from app.plataforma import pulso as pulso_do_worker
from app.plataforma.log import configura_log


async def ao_iniciar(ctx: dict[str, Any]) -> None:
    configura_log(config().log_nivel)
    # Já no boot: esperar o primeiro cron deixaria a instalação nova parecendo sem worker.
    await pulso_do_worker.bate(ctx["redis"])


async def pulso(ctx: dict[str, Any]) -> None:
    """De minuto em minuto: é isto que `/health` lê para saber se há quem processe turno."""
    await pulso_do_worker.bate(ctx["redis"])


async def assumir_conversa(
    ctx: dict[str, Any], cliente_id: str, conversa_id: str, autor_externo: str | None = None
) -> bool:
    """Uma pessoa da equipe assumiu a conversa: o canal mostra isso (no Chatwoot, aberta e atribuída)."""
    async with fabrica_sessao()() as s:
        return await handoff.assumir_no_canal(s, uuid.UUID(cliente_id), uuid.UUID(conversa_id), autor_externo)


async def ingerir_documento(
    ctx: dict[str, Any], cliente_id: str, documento_id: str, texto: str = ""
) -> str:
    """Material novo na base: extrai o texto, divide em trechos e gera os vetores.

    No worker, e não na requisição, porque chama o provedor de embeddings: documento de cem páginas
    são dezenas de chamadas, e a tela não pode ficar esperando isso.
    """
    async with fabrica_sessao()() as s:
        return await conhecimento.ingerir(s, uuid.UUID(cliente_id), uuid.UUID(documento_id), texto)


async def retomada_automatica(ctx: dict[str, Any]) -> int:
    """De minuto em minuto: conversa cujo prazo de handoff venceu volta para o agente."""
    async with fabrica_sessao()() as s:
        return await handoff.retomada_automatica(s)


async def limpar_midia(ctx: dict[str, Any]) -> int:
    """Uma vez por dia, de madrugada: o arquivo que já virou texto sai do disco.

    Diário e não de hora em hora: o arquivo acaba durando de um a dois dias em vez de 24 horas
    cravadas, e ninguém se importa com isso. O que importa é não guardar por semanas.
    """
    async with fabrica_sessao()() as s:
        return await midia.limpa_arquivos_antigos(s)


async def confere_whatsapp(ctx: dict[str, Any]) -> int:
    """De dez em dez minutos: número desconectado do WhatsApp deixa o agente mudo, e isso precisa
    aparecer em Ver consumo e falhas mesmo quando o evento da WAHA não chega."""
    async with fabrica_sessao()() as s:
        return await vigia.confere_sessoes(s, ctx["redis"])


class Configuracao:
    functions = [processar_turno, assumir_conversa, ingerir_documento]
    cron_jobs = [
        cron(pulso, second=30, run_at_startup=True),
        cron(retomada_automatica, second=0, run_at_startup=False),
        cron(confere_whatsapp, minute={0, 10, 20, 30, 40, 50}, second=30, run_at_startup=False),
        cron(limpar_midia, hour=4, minute=7, run_at_startup=False),
    ]
    on_startup = ao_iniciar
    redis_settings = RedisSettings.from_dsn(config().redis_url)
    max_jobs = 20
    job_timeout = 300
