from typing import Any

from arq.connections import RedisSettings

from app.conversas.turno import processar_turno
from app.plataforma.config import config
from app.plataforma.log import configura_log


async def ao_iniciar(ctx: dict[str, Any]) -> None:
    configura_log(config().log_nivel)


class Configuracao:
    functions = [processar_turno]
    on_startup = ao_iniciar
    redis_settings = RedisSettings.from_dsn(config().redis_url)
    max_jobs = 20
    job_timeout = 300
