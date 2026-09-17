import random
from typing import Any

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from pydantic_ai.messages import ModelMessage, ModelResponse, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.conversas import buffer, turno
from app.conversas.divisao import DIGITANDO_MINIMO_SEGUNDOS, tempos_de_digitacao
from app.conversas.modelos import Conversa
from app.ia.ferramentas import calcular
from app.plataforma.config import config
from testes.conftest import ADMIN, cria_cliente_e_agente, envia_webhook, payload_chatwoot


def test_digitando_segue_a_velocidade_com_teto_e_desconta_o_que_ja_passou() -> None:
    sorteio = random.Random(1)
    [curta, media, longa] = tempos_de_digitacao(["oi", "a" * 60, "a" * 1000], 6, 20, sorteio=sorteio)
    assert curta == DIGITANDO_MINIMO_SEGUNDOS
    assert 10 * 0.85 <= media <= 10 * 1.15
    assert longa == 20

    [primeira, segunda] = tempos_de_digitacao(["a" * 60, "a" * 60], 6, 20, ja_passou_segundos=7, sorteio=random.Random(2))
    assert primeira < segunda and primeira >= DIGITANDO_MINIMO_SEGUNDOS

    assert sum(tempos_de_digitacao(["a" * 300] * 10, 6, 30, total_maximo_segundos=90)) == pytest.approx(90)


@pytest.mark.parametrize(
    ("conta", "resultado"),
    [("(199,90 * 3) * 0.9", "539.73"), ("7 // 2", "3"), ("10 / 4", "2.5"), ("2 ** 3", "8"), ("-(5 - 8)", "3")],
)
def test_calculadora_faz_conta_exata(conta: str, resultado: str) -> None:
    assert calcular(conta) == resultado


@pytest.mark.parametrize("perigosa", ["__import__('os').system('ls')", "9 ** 9 ** 9", "1 / 0", "a + 1", "[1] * 9"])
def test_calculadora_recusa_o_que_nao_e_conta(perigosa: str) -> None:
    assert calcular(perigosa).startswith("Erro")


async def test_agente_novo_tem_calculadora_e_busca_e_operador_edita(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    assert agente["ferramentas"] == ["calculadora", "busca_web"]
    assert (agente["digitacao_caracteres_por_segundo"], agente["digitacao_maximo_segundos"]) == (6, 20)

    catalogo = (await http.get("/admin/ferramentas", headers=ADMIN)).json()
    assert [(f["nome"], f["padrao"]) for f in catalogo] == [("calculadora", True), ("busca_web", True)]

    caminho = f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}"
    resp = await http.patch(caminho, json={"ferramentas": ["busca_web"], "digitacao_caracteres_por_segundo": 10}, headers=ADMIN)
    assert resp.status_code == 200, resp.text
    assert resp.json()["ferramentas"] == ["busca_web"] and resp.json()["digitacao_caracteres_por_segundo"] == 10

    assert (await http.patch(caminho, json={"ferramentas": []}, headers=ADMIN)).json()["ferramentas"] == []
    resp = await http.patch(caminho, json={"ferramentas": ["planilha"]}, headers=ADMIN)
    assert resp.status_code == 422 and "planilha" in resp.json()["detail"]
    assert (await http.patch(caminho, json={"digitacao_maximo_segundos": 120}, headers=ADMIN)).status_code == 422


@pytest.fixture
async def redis() -> Any:
    pool = await create_pool(RedisSettings.from_dsn(config().redis_url))
    await pool.flushdb()
    yield pool
    await pool.aclose()


async def test_turno_entrega_ao_modelo_so_as_ferramentas_ligadas(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    vistas: list[set[str]] = []
    instrucoes: list[str] = []
    esperas: list[list[float]] = []

    def responde(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nativas = {f"nativa:{n.kind}" for n in info.model_request_parameters.native_tools}
        vistas.append({t.name for t in info.function_tools} | nativas)
        instrucoes.append(info.instructions or "")
        return ModelResponse(parts=[ToolCallPart(info.output_tools[0].name, {"mensagens": ["Oi Maria, tudo bem?"]})])

    perfis: list[dict[str, Any] | None] = [None, {"supported_native_tools": frozenset()}, None]
    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(responde, profile=perfis[0]))
    monkeypatch.setattr(turno.asyncio, "sleep", lambda s: _registra(esperas, s))
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    caminho = f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}"

    for mensagem_id, ligadas in ((1, None), (2, None), (3, [])):
        if ligadas is not None:
            await http.patch(caminho, json={"ferramentas": ligadas}, headers=ADMIN)
        await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=mensagem_id))
        async with sessao() as s:
            conversa = await s.scalar(select(Conversa))
        token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)
        assert await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), token) == "respondido"
        perfis.pop(0)

    # Modelo com busca nativa usa a do provedor; sem ela, recebe a busca local (DuckDuckGo).
    assert vistas[0] == {"calcular", "transferir_para_humano", "nativa:web_search"}
    assert {"calcular", "transferir_para_humano"} < vistas[1] and not any(v.startswith("nativa:") for v in vistas[1])
    assert vistas[2] == {"transferir_para_humano"}
    # Ferramenta ligada vem com a instrução de quando usar; sem ela o modelo não buscava (v0.8.3).
    assert "use a busca na web" in instrucoes[0] and "Use a calculadora" in instrucoes[0]
    assert "busca na web" not in instrucoes[2] and "calculadora" not in instrucoes[2]
    assert esperas and all(e >= DIGITANDO_MINIMO_SEGUNDOS for e in esperas)


async def _registra(esperas: list[list[float]], segundos: float) -> None:
    esperas.append(segundos)  # type: ignore[arg-type]
