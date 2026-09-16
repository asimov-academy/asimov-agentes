from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from arq import create_pool
from arq.connections import RedisSettings
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.agentes.rotas import router as agentes
from app.clientes.rotas import router as clientes
from app.conversas.webhook import router as webhook
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
app.include_router(clientes)
app.include_router(agentes)
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
