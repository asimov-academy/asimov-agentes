import uuid
from typing import Any

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.consumo.modelos import Falha, Turno
from app.conversas import buffer, turno
from app.conversas.divisao import limita_mensagens
from app.conversas.modelos import Conversa, Mensagem
from app.handoff.servico import MENSAGEM_DE_EXPECTATIVA
from app.plataforma.config import config
from testes.conftest import cria_cliente_e_agente, e_resposta, envia_webhook, payload_chatwoot, resposta_falsa


def modelo_que_responde(mensagens: list[str], recebidas: list[str] | None = None) -> FunctionModel:
    def responde(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if recebidas is not None:
            ultima = historico[-1]
            recebidas.append(str(getattr(ultima.parts[-1], "content", "")))
        return resposta_falsa(info, mensagens)

    return FunctionModel(responde)


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(turno, "tempos_de_digitacao", lambda textos, *a, **k: [0] * len(textos))


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
        "app.ia.provedores.construir_modelo", lambda nome: modelo_que_responde(["Oi Maria!"], recebidas)
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
        "app.ia.provedores.construir_modelo",
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
    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: modelo_que_responde(["oi"]))
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot())
    conversa = await _conversa(sessao)
    canal.status = "open"
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)

    resultado = await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), token)

    assert resultado == "humano_conduz"
    assert canal.enviadas == []


async def test_modelo_fora_do_ar_registra_turno_com_erro_avisa_e_transfere(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    def quebra(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise RuntimeError("provedor fora do ar")

    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(quebra))
    monkeypatch.setattr(turno, "_espera", _sem_sono)
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot())
    conversa = await _conversa(sessao)
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)

    resultado = await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), token)

    assert resultado == "falhou"
    assert [t for _, t in canal.enviadas] == [MENSAGEM_DE_EXPECTATIVA]
    assert len(canal.transferencias) == 1
    nota = canal.transferencias[0][2]
    assert "não conseguiu responder" in nota and "Resumo automático indisponível" in nota and "oi" in nota
    async with sessao() as s:
        registro = await s.scalar(select(Turno))
        falhas = set(await s.scalars(select(Falha.tipo)))
    assert registro is not None and "provedor fora do ar" in (registro.erro or "")
    assert falhas == {"turno_modelo_falhou", "resumo_handoff_falhou"}


async def test_turno_de_outro_cliente_nao_acha_conversa(http, canal, fila, sessao, redis) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot())
    conversa = await _conversa(sessao)
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)

    resultado = await turno.processar_turno({"redis": redis}, str(uuid.uuid4()), str(conversa.id), token)

    assert resultado == "sem_conversa"


async def _sem_sono(segundos: float) -> None:
    return None


async def test_fallback_responde_quando_o_principal_falha(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from pydantic_ai.exceptions import ModelHTTPError

    def fora_do_ar(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        raise ModelHTTPError(status_code=503, model_name="gpt-5.5", body="indisponível")

    monkeypatch.setattr(
        "app.ia.provedores.construir_modelo",
        lambda nome: FunctionModel(fora_do_ar) if nome.startswith("openai:") else modelo_que_responde(["Respondi pelo fallback"]),
    )
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    assert agente["modelo_fallback"] == "groq:llama-3.3-70b-versatile"
    await envia_webhook(http, agente["token"], payload_chatwoot())
    conversa = await _conversa(sessao)
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)

    resultado = await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), token)

    assert resultado == "respondido"
    assert [t for _, t in canal.enviadas] == ["Respondi pelo fallback"]


def test_constroi_modelo_de_cada_provedor() -> None:
    from pydantic_ai.models.fallback import FallbackModel
    from pydantic_ai.models.groq import GroqModel
    from pydantic_ai.models.openai import OpenAIResponsesModel
    from pydantic_ai.native_tools import WebSearchTool

    from app.ia.provedores import construir_modelo, modelo_de_resposta

    assert isinstance(construir_modelo("groq:whisper-large-v3-turbo"), GroqModel)
    assert isinstance(modelo_de_resposta("openai:gpt-5.5", None), OpenAIResponsesModel)
    assert isinstance(modelo_de_resposta("openai:gpt-5.5", "groq:llama-3.3-70b-versatile"), FallbackModel)

    def busca_nativa(nome: str) -> bool:
        return WebSearchTool in construir_modelo(nome).profile.get("supported_native_tools", frozenset())

    # OpenAI pela Responses tem busca nativa; Groq só nos compound (nos outros a busca cai na local).
    assert busca_nativa("openai:gpt-5.5")
    assert not busca_nativa("groq:llama-3.3-70b-versatile")
    assert busca_nativa("groq:groq/compound")


async def test_mensagem_que_chega_durante_o_turno_e_respondida_no_seguinte(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    recebidas: list[str] = []
    chegou_durante: list[bool] = []

    def responde(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        recebidas.append(str(historico[-1].parts[-1].content))  # type: ignore[union-attr]
        return resposta_falsa(info, ["ok"])

    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(responde))
    enviar_original = canal.enviar_texto

    async def envia_e_contato_escreve(credenciais, conversa_externa, texto):  # type: ignore[no-untyped-def]
        if not chegou_durante:
            chegou_durante.append(True)
            await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=2, conteudo="e o frete?"))
        return await enviar_original(credenciais, conversa_externa, texto)

    monkeypatch.setattr(canal, "enviar_texto", envia_e_contato_escreve)
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=1, conteudo="quanto custa?"))
    conversa = await _conversa(sessao)

    primeiro = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)
    assert await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), primeiro) == "respondido"
    segundo = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)
    assert await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), segundo) == "respondido"

    assert recebidas == ["quanto custa?", "e o frete?"]


def test_fala_de_atendente_encerra_pendencias_anteriores() -> None:
    from datetime import UTC, datetime, timedelta

    base = datetime(2026, 9, 16, tzinfo=UTC)

    def fala(autor: str, minuto: int) -> Mensagem:
        return Mensagem(id=uuid.uuid4(), autor=autor, texto=f"{autor}{minuto}", criado_em=base + timedelta(minutes=minuto))

    mensagens = [fala("contato", 1), fala("agente", 3), fala("contato", 2), fala("humano", 4), fala("contato", 5)]

    _, pendentes = turno.separa_pendentes(mensagens[:3], respondido_ate=base + timedelta(minutes=1))
    assert [m.texto for m in pendentes] == ["contato2"]
    _, pendentes = turno.separa_pendentes(mensagens, respondido_ate=base + timedelta(minutes=1))
    assert [m.texto for m in pendentes] == ["contato5"]
    _, pendentes = turno.separa_pendentes(mensagens[:3], respondido_ate=None)
    assert [m.texto for m in pendentes] == ["contato2"]


async def test_mensagem_que_chega_enquanto_o_modelo_pensa_e_respondida_junto(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    recebidas: list[str] = []
    tokens: list[str] = []

    async def responde(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        recebidas.append(str(historico[-1].parts[-1].content))  # type: ignore[union-attr]
        if len(recebidas) == 1:
            await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=2, conteudo="e o frete?"))
            tokens.append(await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1))
        return resposta_falsa(info, ["Custa 50 e o frete é grátis"])

    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(responde))
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=1, conteudo="quanto custa?"))
    conversa = await _conversa(sessao)
    primeiro = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)

    assert await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), primeiro) == "substituido"
    assert canal.enviadas == []
    assert await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), tokens[0]) == "respondido"

    assert recebidas == ["quanto custa?", "quanto custa?\ne o frete?"]
    assert [t for _, t in canal.enviadas] == ["Custa 50 e o frete é grátis"]
    async with sessao() as s:
        erros = list(await s.scalars(select(Turno.erro).order_by(Turno.criado_em)))
    assert erros[0] is not None and erros[0].startswith("descartada") and erros[1] is None


def test_raciocinio_baixo_so_nos_modelos_openai_que_vem_com_ele_desligado(monkeypatch: pytest.MonkeyPatch) -> None:
    from app.ia.provedores import construir_modelo
    from app.plataforma.config import config

    def esforco(nome: str) -> str | None:
        return (construir_modelo(nome).settings or {}).get("openai_reasoning_effort")

    # Na VPS, o gpt-5.1 sem raciocínio buscava e não usava o resultado.
    assert esforco("openai:gpt-5.1") == "low"
    assert esforco("openai:gpt-5.5") is None and esforco("openai:gpt-5-mini") is None
    assert esforco("openai:gpt-4o") is None and esforco("groq:llama-3.3-70b-versatile") is None

    monkeypatch.setattr(config(), "openai_raciocinio", "medium")
    assert esforco("openai:gpt-5.1") == "medium"
    monkeypatch.setattr(config(), "openai_raciocinio", "none")
    assert esforco("openai:gpt-5.1") is None


def test_saida_nativa_so_quando_todo_modelo_do_agente_aceita() -> None:
    from pydantic_ai import NativeOutput

    from app.ia.agente import Resposta, tipo_de_saida
    from app.ia.provedores import modelo_de_resposta

    assert isinstance(tipo_de_saida(modelo_de_resposta("openai:gpt-5.1", None)), NativeOutput)
    assert isinstance(tipo_de_saida(modelo_de_resposta("openai:gpt-5.5", "groq:openai/gpt-oss-120b")), NativeOutput)
    # Llama da Groq não tem saída estruturada nativa: o agente inteiro fica na tool de resposta.
    assert tipo_de_saida(modelo_de_resposta("openai:gpt-5.1", "groq:llama-3.3-70b-versatile")) is Resposta


@pytest.mark.parametrize("nativo", [True, False])
async def test_resposta_fora_do_formato_e_corrigida_e_registrada(http, canal, fila, sessao, redis, monkeypatch, nativo) -> None:  # type: ignore[no-untyped-def]
    chamadas: list[str] = []

    def erra_e_corrige(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        chamadas.append(info.model_request_parameters.output_mode)
        if len(chamadas) == 1:
            # Na VPS o modelo errou o formato e o aviso de correção virou "mensagem do contato".
            return ModelResponse(parts=[TextPart("{}" if nativo else "texto solto sem a tool")])
        return resposta_falsa(info, ["A PTAX de ontem fechou em R$ 5,15"])

    perfil = {"supports_json_schema_output": nativo}
    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(erra_e_corrige, profile=perfil))
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot(conteudo="qual o dólar de ontem?"))
    conversa = await _conversa(sessao)
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)

    assert await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), token) == "respondido"
    assert chamadas == (["native", "native"] if nativo else ["tool", "tool"])
    assert [t for _, t in canal.enviadas] == ["A PTAX de ontem fechou em R$ 5,15"]
    async with sessao() as s:
        [falha] = list(await s.scalars(select(Falha).where(Falha.tipo == "resposta_corrigida")))
    assert falha.detalhe["avisos"] and falha.agente_id is not None
