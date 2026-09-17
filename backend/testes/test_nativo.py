"""Agente nativo: conversa no terminal com o mesmo buffer, turno, consumo e handoff dos canais."""

from typing import Any

import httpx
import pytest
from arq import create_pool
from arq.connections import RedisSettings
from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.acessos.modelos import AcessoCanal
from app.consumo.modelos import Turno
from app.conversas import turno
from app.conversas.modelos import Conversa, Mensagem
from app.plataforma.config import config
from testes.conftest import ADMIN, cria_cliente_e_agente
from testes.test_handoff import ModeloQueTransfere


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(turno, "tempos_de_digitacao", lambda textos, *a, **k: [0] * len(textos))


@pytest.fixture
async def redis() -> Any:
    pool = await create_pool(RedisSettings.from_dsn(config().redis_url))
    await pool.flushdb()
    yield pool
    await pool.aclose()


async def cria_nativo(http: httpx.AsyncClient, nome_cliente: str = "Loja Exemplo", nome: str = "Ana", **extra: Any) -> dict[str, Any]:
    cliente = (await http.post("/admin/clientes", json={"nome": nome_cliente}, headers=ADMIN)).json()
    resp = await http.post(
        f"/admin/clientes/{cliente['id']}/agentes", json={"nome": nome, "canal": "nativo", **extra}, headers=ADMIN
    )
    assert resp.status_code == 201, resp.text
    return resp.json()


def _terminal(agente: dict[str, Any], cliente_id: str | None = None) -> str:
    return f"/admin/clientes/{cliente_id or agente['cliente_id']}/agentes/{agente['id']}/terminal"


async def _manda(http: httpx.AsyncClient, agente: dict[str, Any], texto: str, conversa: str | None = None) -> dict[str, Any]:
    resp = await http.post(_terminal(agente), json={"texto": texto, "conversa": conversa}, headers=ADMIN)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _le(http: httpx.AsyncClient, agente: dict[str, Any], conversa: str, depois: int = 0) -> dict[str, Any]:
    resp = await http.get(f"{_terminal(agente)}/{conversa}", params={"depois": depois}, headers=ADMIN)
    assert resp.status_code == 200, resp.text
    return resp.json()


async def _roda_turno(fila: Any, redis: Any) -> str:
    _, cliente_id, conversa_id, token = fila.jobs[-1]
    await redis.set(f"buffer:{conversa_id}", token)
    return await turno.processar_turno({"redis": redis}, cliente_id, conversa_id, token)


def _responde(*mensagens: str) -> FunctionModel:
    def responde(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if not info.output_tools:
            return ModelResponse(parts=[TextPart("resumo")])
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"mensagens": list(mensagens)})])

    return FunctionModel(responde)


async def test_cria_nativo_sem_conexao_nem_token(http, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_nativo(http, handoff_destino={"numero": "5511999990000"})

    assert agente["canal"] == "nativo"
    assert agente["credenciais"] == {} and agente["handoff_destino"] is None
    async with sessao() as s:
        assert list(await s.scalars(select(AcessoCanal))) == []


async def test_conversa_no_terminal_responde_com_digitando_e_registra_consumo(http, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: _responde("Oi!", "Como posso ajudar?"))
    agente = await cria_nativo(http, buffer_segundos=2)
    digitando: list[bool] = []
    original = turno._digitando

    async def espia(canal, credenciais, conversa, ligado):  # type: ignore[no-untyped-def]
        digitando.append(ligado)
        await original(canal, credenciais, conversa, ligado)

    monkeypatch.setattr(turno, "_digitando", espia)

    enviada = await _manda(http, agente, "oi")
    await _manda(http, agente, "tudo bem?", enviada["conversa"])
    assert enviada["agendada"] and fila.adiamentos == [2, 2]

    assert await _roda_turno(fila, redis) == "respondido"

    leitura = await _le(http, agente, enviada["conversa"])
    assert [m["texto"] for m in leitura["mensagens"]] == ["Oi!", "Como posso ajudar?"]
    assert leitura["proxima"] == 2 and leitura["handoff"] is None
    assert leitura["digitando"] is False and leitura["respondendo"] is False
    assert (await _le(http, agente, enviada["conversa"], depois=2))["mensagens"] == []
    assert True in digitando and digitando[-1] is False

    async with sessao() as s:
        textos = [(m.autor, m.texto) for m in await s.scalars(select(Mensagem).order_by(Mensagem.criado_em))]
        turnos = list(await s.scalars(select(Turno)))
    assert textos == [("contato", "oi"), ("contato", "tudo bem?"), ("agente", "Oi!"), ("agente", "Como posso ajudar?")]
    assert len(turnos) == 1 and turnos[0].erro is None


async def test_sem_conversa_comeca_outra(http, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_nativo(http)

    primeira = await _manda(http, agente, "oi")
    segunda = await _manda(http, agente, "oi de novo")

    assert primeira["conversa"] != segunda["conversa"]
    async with sessao() as s:
        assert len(list(await s.scalars(select(Conversa)))) == 2


async def test_handoff_no_terminal_mostra_codigo_cala_o_agente_e_retoma(http, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(ModeloQueTransfere()))
    agente = await cria_nativo(http)
    enviada = await _manda(http, agente, "quero falar com uma pessoa")

    assert await _roda_turno(fila, redis) == "transferido"

    leitura = await _le(http, agente, enviada["conversa"])
    assert [m["texto"] for m in leitura["mensagens"]] == ["Vou chamar alguém da equipe"]
    assert leitura["handoff"]["motivo"] == "contato pediu para falar com uma pessoa"
    assert len(leitura["handoff"]["codigo"]) == 6

    calada = await _manda(http, agente, "alô?", enviada["conversa"])
    assert calada["agendada"] is False and len(fila.jobs) == 1

    resp = await http.post(f"/admin/clientes/{agente['cliente_id']}/conversas/{enviada['conversa_id']}/retomar", headers=ADMIN)
    assert resp.json() == {"retomado": True}
    assert (await _le(http, agente, enviada["conversa"]))["handoff"] is None
    assert (await _manda(http, agente, "voltei", enviada["conversa"]))["agendada"] is True


async def test_conversa_do_terminal_isolada_por_cliente(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    ana = await cria_nativo(http, "Loja Exemplo", "Ana")
    bia = await cria_nativo(http, "Padaria Pão Quente", "Bia")
    conversa = (await _manda(http, ana, "segredo da loja"))["conversa"]

    outro_cliente = await http.get(f"{_terminal(ana, bia['cliente_id'])}/{conversa}", headers=ADMIN)
    outro_agente = await http.get(f"{_terminal(bia)}/{conversa}", headers=ADMIN)
    manda_na_alheia = await http.post(_terminal(bia), json={"texto": "oi", "conversa": conversa}, headers=ADMIN)

    assert (outro_cliente.status_code, outro_agente.status_code, manda_na_alheia.status_code) == (404, 404, 404)


async def test_terminal_so_com_agente_nativo(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    chatwoot = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    resp = await http.post(_terminal(chatwoot), json={"texto": "oi"}, headers=ADMIN)
    vazia = await http.post(_terminal(chatwoot), json={"texto": "   "}, headers=ADMIN)
    sem_chave = await http.post(_terminal(chatwoot), json={"texto": "oi"})

    assert (resp.status_code, vazia.status_code, sem_chave.status_code) == (422, 422, 401)


async def test_nativo_sem_webhook(http, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_nativo(http)
    token = agente["url_webhook"].rsplit("/", 1)[1]

    resp = await http.post(f"/webhook/nativo/{token}", json={"texto": "oi"})

    assert resp.status_code == 401


async def test_remover_e_renomear_nativo_sem_token(http, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_nativo(http)
    caminho = f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}"

    renomeado = await http.patch(caminho, json={"nome": "Ana Paula"}, headers=ADMIN)
    removido = await http.request("DELETE", caminho, json={"confirmacao": "Ana Paula"}, headers=ADMIN)

    assert renomeado.status_code == 200 and removido.json() == {"removido": True, "canal_desconectado": True}
