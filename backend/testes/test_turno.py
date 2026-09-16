import uuid
from typing import Any

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.consumo.modelos import Turno
from app.conversas import buffer, turno
from app.conversas.divisao import limita_mensagens
from app.conversas.modelos import Conversa, Mensagem
from app.plataforma.config import config
from testes.conftest import cria_cliente_e_agente, envia_webhook, payload_chatwoot


def modelo_que_responde(mensagens: list[str], recebidas: list[str] | None = None) -> FunctionModel:
    def responde(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if recebidas is not None:
            ultima = historico[-1]
            recebidas.append(str(getattr(ultima.parts[-1], "content", "")))
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"mensagens": mensagens})])

    return FunctionModel(responde)


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(turno, "delay_ms", lambda texto: 0)


@pytest.fixture
async def redis() -> Any:
    pool = await create_pool(RedisSettings.from_dsn(config().redis_url))
    await pool.flushdb()
    yield pool
    await pool.aclose()


async def _conversa(sessao) -> Conversa:  # type: ignore[no-untyped-def]
    async with sessao() as s:
        conversa = await s.scalar(select(Conversa))
    assert conversa is not None
    return conversa


def test_divisao_nunca_passa_do_maximo() -> None:
    assert limita_mensagens(["a", "b", "c", "d", "e"], 3) == ["a", "b", "c\n\nd\n\ne"]
    assert limita_mensagens(["  ", "a", ""], 3) == ["a"]
    assert limita_mensagens(["a", "b"], 1) == ["a\n\nb"]


async def test_tres_mensagens_no_buffer_geram_um_turno(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    recebidas: list[str] = []
    monkeypatch.setattr(
        "app.ia.agente.construir_modelo", lambda nome: modelo_que_responde(["Oi Maria!"], recebidas)
    )
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    for i, texto in enumerate(["oi", "quero saber", "quanto eu devo"], start=1):
        await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=i, conteudo=texto))

    conversa = await _conversa(sessao)
    tokens = []
    for _ in range(3):
        tokens.append(await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1))

    resultados = [
        await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), t)
        for t in tokens
    ]

    assert resultados == ["substituido", "substituido", "respondido"]
    assert [t for _, t in canal.enviadas] == ["Oi Maria!"]
    assert recebidas == ["oi\nquero saber\nquanto eu devo"]


async def test_resposta_dividida_respeita_maximo_e_registra_turno(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(
        "app.ia.agente.construir_modelo",
        lambda nome: modelo_que_responde(["um", "dois", "três", "quatro", "cinco"]),
    )
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana", max_mensagens_por_resposta=2)
    await envia_webhook(http, agente["token"], payload_chatwoot())
    conversa = await _conversa(sessao)
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)

    await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), token)

    assert len(canal.enviadas) == 2
    assert canal.digitando_chamadas[0] is True and canal.digitando_chamadas[-1] is False
    async with sessao() as s:
        registro = await s.scalar(select(Turno))
        saidas = list(await s.scalars(select(Mensagem).where(Mensagem.autor == "agente")))
    assert registro is not None and registro.erro is None
    assert registro.tokens_entrada > 0 and registro.modelo == "openai:gpt-5.5"
    assert len(saidas) == 2


async def test_humano_conduzindo_o_agente_nao_responde(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("app.ia.agente.construir_modelo", lambda nome: modelo_que_responde(["oi"]))
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot())
    conversa = await _conversa(sessao)
    canal.status = "open"
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)

    resultado = await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), token)

    assert resultado == "humano_conduz"
    assert canal.enviadas == []


async def test_modelo_fora_do_ar_registra_turno_com_erro_e_nao_responde(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def quebra(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise RuntimeError("provedor fora do ar")

    monkeypatch.setattr("app.ia.agente.construir_modelo", lambda nome: FunctionModel(quebra))
    monkeypatch.setattr(turno, "_espera", _sem_sono)
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot())
    conversa = await _conversa(sessao)
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)

    resultado = await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), token)

    assert resultado == "falhou"
    assert canal.enviadas == []
    async with sessao() as s:
        registro = await s.scalar(select(Turno))
    assert registro is not None and "provedor fora do ar" in (registro.erro or "")


async def test_turno_de_outro_cliente_nao_acha_conversa(http, canal, fila, sessao, redis) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot())
    conversa = await _conversa(sessao)
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)

    resultado = await turno.processar_turno({"redis": redis}, str(uuid.uuid4()), str(conversa.id), token)

    assert resultado == "sem_conversa"


async def _sem_sono(segundos: float) -> None:
    return None
