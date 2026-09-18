"""Worker do copiloto: um processo só, num contêiner só.

Separado do worker de atendimento de propósito. O turno de um agente responde a um contato e
precisa ser rápido; o turno do copiloto chama um CLI que pensa por minutos. Misturar os dois
significaria dar ao atendimento o `job_timeout` do copiloto, ou o contrário.

O contêiner deste worker é o único que leva o CLI, o Node e a pasta de credencial montada. A API
não ganha nada disso: ela só enfileira.
"""

from typing import Any

import structlog
from arq.connections import RedisSettings

from app.copiloto import sessao as sessao_do_copiloto
from app.copiloto import servico
from app.plataforma.config import config
from app.plataforma.log import configura_log

log = structlog.get_logger()

FILA = servico.FILA


async def ao_iniciar(ctx: dict[str, Any]) -> None:
    configura_log(config().log_nivel)


async def turno_do_copiloto(ctx: dict[str, Any], texto: str) -> bool:
    """Um pedido do operador, do começo ao fim. Falha vira recado na tela, nunca job perdido."""
    await sessao_do_copiloto.muda(estado="pensando", erro="")
    atual = await sessao_do_copiloto.ler()
    try:
        resposta, conversa = await servico.roda_turno(texto, atual.get("conversa_cli", ""))
    except servico.CopilotoIndisponivel as erro:
        await sessao_do_copiloto.muda(estado="parado", erro=str(erro))
        return False
    except Exception as erro:  # noqa: BLE001
        log.error("copiloto_erro", erro=repr(erro))
        await sessao_do_copiloto.muda(estado="parado", erro="o copiloto falhou; tente de novo")
        return False

    await sessao_do_copiloto.anota_mensagem("copiloto", resposta)
    await sessao_do_copiloto.muda(estado="parado", conversa_cli=conversa)
    return True


async def melhorar_texto(ctx: dict[str, Any], texto: str, empresa: str) -> str:
    """O botão de estrelinha do onboarding, pela assinatura do operador em vez de chave de API.

    A instrução é a mesma do caminho por chave (`ia/redacao.py`), inclusive a delimitação do texto
    do operador: ele é material a reescrever, nunca instrução para o modelo.
    """
    from app.ia import redacao

    pedido = (
        f"{redacao.INSTRUCAO}\n\nEmpresa: {empresa or 'sem nome informado'}\n\n"
        f"<material>\n{texto[: redacao.LIMITE_DE_ENTRADA]}\n</material>"
    )
    melhorado = (await servico.redige(pedido)).strip()
    return melhorado[: redacao.LIMITE_DE_SAIDA] or texto


class Configuracao:
    functions = [turno_do_copiloto, melhorar_texto]
    on_startup = ao_iniciar
    redis_settings = RedisSettings.from_dsn(config().redis_url)
    queue_name = FILA
    # Um turno de cada vez: a assinatura tem limite por janela, e o operador é um só.
    max_jobs = 1
    # Folga sobre o tempo limite do próprio CLI (`servico.TEMPO_LIMITE_SEGUNDOS`), para quem
    # interrompe ser o nosso timeout, com mensagem em português, e não o arq.
    job_timeout = servico.TEMPO_LIMITE_SEGUNDOS + 60
