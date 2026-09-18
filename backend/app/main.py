import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.agentes.rotas import router as agentes
from app.canais.nativo.rotas import router as terminal
from app.canais.waha.rotas import router as waha
from app.canais.whatsapp.rotas import router as whatsapp
from app.clientes.rotas import router as clientes
from app.consumo.rotas import router as consumo
from app.conversas.webhook import router as webhook
from app.handoff.rotas import router as handoff
from app.plataforma.banco import fabrica_sessao
from app.plataforma.config import config
from app.painel.rotas import router as painel
from app.painel.rotas_admin import router as painel_admin
from app.plataforma.log import configura_log
from app.plataforma import pulso as pulso_do_worker
from app.plataforma.publico import router as publico


@asynccontextmanager
async def ciclo(app: FastAPI) -> AsyncIterator[None]:
    configura_log(config().log_nivel)
    app.state.fila = await create_pool(RedisSettings.from_dsn(config().redis_url))
    yield
    await app.state.fila.aclose()


app = FastAPI(title="Asimov Agentes", lifespan=ciclo, docs_url=None, redoc_url=None)
log = structlog.get_logger()


def caminho_sem_segredo(caminho: str) -> str:
    """O token do webhook é o segredo do agente e está na URL: não pode ir para log nenhum.

    `/webhook/chatwoot/<token>` vira `/webhook/chatwoot/…` (auditoria de 2026-09-18, A14).
    """
    partes = caminho.split("/")
    if len(partes) > 3 and partes[1] == "webhook":
        return "/".join([*partes[:3], "…"])
    return caminho


@app.exception_handler(Exception)
async def erro_interno(request: Request, erro: Exception) -> JSONResponse:
    """Fora de `/admin` a resposta é sempre igual, com uma referência para achar no log.

    Nas rotas `/admin` (só localhost, chamadas pelo setup) o motivo vai junto: quem chama ali é o
    operador, na própria VPS, e é o que o menu mostra quando algo falha.
    """
    referencia = uuid.uuid4().hex[:12]
    log.error(
        "erro_interno",
        referencia=referencia,
        caminho=caminho_sem_segredo(request.url.path),
        erro=repr(erro)[:500],
    )
    if request.url.path.startswith("/admin"):
        return JSONResponse(
            {"detail": f"erro interno: {type(erro).__name__}: {erro}", "referencia": referencia},
            status_code=500,
        )
    return JSONResponse({"detail": "erro interno", "referencia": referencia}, status_code=500)


app.include_router(clientes)
app.include_router(agentes)
app.include_router(consumo)
app.include_router(handoff)
app.include_router(terminal)
app.include_router(waha)
app.include_router(whatsapp)
app.include_router(webhook)
app.include_router(publico)
# O painel só existe quando o operador escolheu administrar pelo navegador. Desligado, nem a rota
# de login responde, e o Caddy nem publica o host.
# O setup pergunta o estado e gera o código de primeiro acesso mesmo com o painel desligado: é assim
# que ele liga o painel. Já as telas só existem quando o operador escolheu o navegador.
app.include_router(painel_admin)
if config().painel_ativo:
    app.include_router(painel)


@app.get("/health")
async def health() -> JSONResponse:
    """API, banco, Redis e worker.

    O worker entra porque API saudável com worker parado é a instalação inteira muda: mensagem
    chega, é gravada, e ninguém responde (auditoria de 2026-09-18, A20). `aguardando` é a
    instalação que ainda não viu o worker subir nenhuma vez, e não derruba a saúde: é o estado
    normal durante a própria instalação.
    """
    estado = {"api": "ok", "banco": "ok", "redis": "ok", "worker": "ok"}
    try:
        async with fabrica_sessao()() as s:
            await s.execute(text("select 1"))
    except Exception:
        estado["banco"] = "erro"
    try:
        await app.state.fila.ping()
        estado["worker"] = await pulso_do_worker.estado(app.state.fila)
    except Exception:
        estado["redis"] = "erro"
        estado["worker"] = "desconhecido"
    ok = all(v in ("ok", "aguardando") for v in estado.values())
    return JSONResponse(estado, status_code=200 if ok else 503)
