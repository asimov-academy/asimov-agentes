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
from app.clientes.rotas import router as clientes
from app.consumo.rotas import router as consumo
from app.conversas.webhook import router as webhook
from app.handoff.rotas import router as handoff
from app.plataforma.banco import fabrica_sessao
from app.plataforma.config import config
from app.plataforma.log import configura_log


@asynccontextmanager
async def ciclo(app: FastAPI) -> AsyncIterator[None]:
    configura_log(config().log_nivel)
    app.state.fila = await create_pool(RedisSettings.from_dsn(config().redis_url))
    yield
    await app.state.fila.aclose()


app = FastAPI(title="Asimov Agentes", lifespan=ciclo, docs_url=None, redoc_url=None)
log = structlog.get_logger()


@app.exception_handler(Exception)
async def erro_interno(request: Request, erro: Exception) -> JSONResponse:
    """Nas rotas /admin (só localhost, chamadas pelo setup) o motivo vai na resposta."""
    log.error("erro_interno", caminho=request.url.path, erro=repr(erro)[:500])
    if request.url.path.startswith("/admin"):
        return JSONResponse({"detail": f"erro interno: {type(erro).__name__}: {erro}"}, status_code=500)
    return JSONResponse({"detail": "erro interno"}, status_code=500)


app.include_router(clientes)
app.include_router(agentes)
app.include_router(consumo)
app.include_router(handoff)
app.include_router(terminal)
app.include_router(waha)
app.include_router(webhook)


@app.get("/health")
async def health() -> JSONResponse:
    estado = {"api": "ok", "banco": "ok", "redis": "ok"}
    try:
        async with fabrica_sessao()() as s:
            await s.execute(text("select 1"))
    except Exception:
        estado["banco"] = "erro"
    try:
        await app.state.fila.ping()
    except Exception:
        estado["redis"] = "erro"
    ok = all(v == "ok" for v in estado.values())
    return JSONResponse(estado, status_code=200 if ok else 503)
