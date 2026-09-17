import uuid
from typing import Any

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from pydantic_ai.messages import ModelMessage, ModelRequest, ModelResponse, TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.consumo.modelos import Falha, Turno
from app.conversas import buffer, turno
from app.conversas.modelos import Conversa
from app.handoff import servico as handoff
from app.handoff.modelos import Handoff
from app.plataforma.config import config
from testes.conftest import ADMIN, cria_cliente_e_agente, e_resposta, envia_webhook, payload_chatwoot, resposta_falsa

RESUMO = "Maria quer trocar um produto com defeito e já enviou o número do pedido"
DESTINO = {"tipo": "usuario", "id": 7, "nome": "Joana"}


class ModeloQueTransfere:
    """Pede humano na primeira chamada, responde depois do retorno da tool e resume quando é o auxiliar."""

    def __init__(self, transfere: bool = True) -> None:
        self.transfere = transfere

    def __call__(self, historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if not e_resposta(info):
            return ModelResponse(parts=[TextPart(RESUMO)])
        ultima = historico[-1]
        voltou_da_tool = isinstance(ultima, ModelRequest) and any(isinstance(p, ToolReturnPart) for p in ultima.parts)
        if self.transfere and not voltou_da_tool:
            return ModelResponse(parts=[ToolCallPart("transferir_para_humano", {"motivo": "contato pediu para falar com uma pessoa"})])
        texto = "Vou chamar alguém da equipe" if voltou_da_tool else "Posso ajudar"
        return resposta_falsa(info, [texto])


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(turno, "tempos_de_digitacao", lambda textos, *a, **k: [0] * len(textos))


@pytest.fixture
def modelo(monkeypatch: pytest.MonkeyPatch) -> ModeloQueTransfere:
    falso = ModeloQueTransfere()
    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(falso))
    return falso


@pytest.fixture
async def redis() -> Any:
    pool = await create_pool(RedisSettings.from_dsn(config().redis_url))
    await pool.flushdb()
    yield pool
    await pool.aclose()


async def _turno(sessao: Any, redis: Any) -> str:
    async with sessao() as s:
        conversa = await s.scalar(select(Conversa))
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)
    return await turno.processar_turno({"redis": redis}, str(conversa.cliente_id), str(conversa.id), token)


async def _handoffs(sessao: Any) -> list[Handoff]:
    async with sessao() as s:
        return list(await s.scalars(select(Handoff).order_by(Handoff.iniciado_em)))


def _devolucao(conversa: int = 1532, inbox: int = 3) -> dict[str, Any]:
    return {
        "event": "conversation_status_changed",
        "id": conversa,
        "status": "pending",
        "inbox_id": inbox,
        "changed_attributes": [{"status": {"previous_value": "open", "current_value": "pending"}}],
    }


async def test_contato_pede_humano_e_a_conversa_vai_atribuida_com_resumo(http, canal, fila, sessao, redis, modelo) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana", handoff_destino=DESTINO)
    await envia_webhook(http, agente["token"], payload_chatwoot(conteudo="quero falar com uma pessoa"))

    assert await _turno(sessao, redis) == "transferido"

    assert [t for _, t in canal.enviadas] == ["Vou chamar alguém da equipe"]
    [(conversa, destino, nota)] = canal.transferencias
    assert conversa == "1532" and destino == DESTINO
    assert nota == f"Motivo: contato pediu para falar com uma pessoa\n{RESUMO}"
    [registro] = await _handoffs(sessao)
    assert registro.resumo == RESUMO and registro.destino == DESTINO and registro.retomado_em is None
    assert len(registro.codigo) == 6
    async with sessao() as s:
        assert (await s.scalar(select(Conversa))).status == "humano"
        turnos = {t.funcao: t for t in await s.scalars(select(Turno))}
    assert turnos["resposta"].tools_chamadas == ["transferir_para_humano"]
    assert turnos["resumo_handoff"].modelo == agente["modelo_auxiliar"]


async def test_conversa_com_humano_nao_gera_resposta(http, canal, fila, sessao, redis, modelo) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=1, conteudo="quero falar com uma pessoa"))
    assert await _turno(sessao, redis) == "transferido"
    fila.jobs.clear()

    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=2, conteudo="alô?", status="open"))

    assert fila.jobs == []
    assert await _turno(sessao, redis) == "humano_conduz"
    assert len(canal.enviadas) == 1 and len(canal.transferencias) == 1


async def test_devolver_para_pendente_fecha_o_handoff_e_o_agente_volta(http, canal, fila, sessao, redis, modelo) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=1, conteudo="quero falar com uma pessoa"))
    assert await _turno(sessao, redis) == "transferido"

    canal.status = "pending"
    # O Chatwoot manda a mesma devolução em dois eventos.
    assert (await envia_webhook(http, agente["token"], _devolucao())).status_code == 200
    assert (await envia_webhook(http, agente["token"], {**_devolucao(), "event": "conversation_updated"})).status_code == 200

    [registro] = await _handoffs(sessao)
    assert registro.retomado_em is not None and registro.retomado_por == "chatwoot"
    async with sessao() as s:
        assert (await s.scalar(select(Conversa))).status == "agente"

    modelo.transfere = False
    fila.jobs.clear()
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=2, conteudo="voltei"))
    assert [j[0] for j in fila.jobs] == ["processar_turno"]
    assert await _turno(sessao, redis) == "respondido"
    assert canal.enviadas[-1][1] == "Posso ajudar"


async def test_devolucao_que_nao_chegou_e_fechada_no_turno(http, canal, fila, sessao, redis, modelo) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=1, conteudo="quero falar com uma pessoa"))
    assert await _turno(sessao, redis) == "transferido"

    canal.status = "pending"
    modelo.transfere = False
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=2, conteudo="voltei"))

    assert await _turno(sessao, redis) == "respondido"
    [registro] = await _handoffs(sessao)
    assert registro.retomado_por == "chatwoot"


async def test_devolucao_de_outro_agente_nao_fecha_handoff(http, canal, fila, sessao, redis, modelo) -> None:  # type: ignore[no-untyped-def]
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    outro = await cria_cliente_e_agente(http, "Padaria", "Bia")
    await envia_webhook(http, ana["token"], payload_chatwoot(conteudo="quero falar com uma pessoa"))
    assert await _turno(sessao, redis) == "transferido"

    await envia_webhook(http, outro["token"], _devolucao())

    [registro] = await _handoffs(sessao)
    assert registro.retomado_em is None


async def test_handoff_idempotente(http, canal, fila, sessao, modelo) -> None:  # type: ignore[no-untyped-def]
    agente_api = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente_api["token"], payload_chatwoot())

    resultados = []
    for _ in range(2):
        async with sessao() as s:
            conversa = await s.scalar(select(Conversa))
            agente = await agentes_repo.obter(s, conversa.cliente_id, conversa.agente_id)
            resultados.append(
                await handoff.transferir(s, agente, canal, agentes_servico.credenciais(agente), conversa, "pediu humano")
            )
            await s.commit()

    assert resultados == ["transferido", "ja_aberto"]
    assert len(canal.transferencias) == 1
    assert len(await _handoffs(sessao)) == 1


async def test_canal_fora_do_ar_nao_registra_handoff(http, canal, fila, sessao, redis, modelo) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    canal.transferir_quebra = True
    await envia_webhook(http, agente["token"], payload_chatwoot(conteudo="quero falar com uma pessoa"))

    assert await _turno(sessao, redis) == "respondido"

    assert await _handoffs(sessao) == []
    async with sessao() as s:
        assert "handoff_falhou" in set(await s.scalars(select(Falha.tipo)))
        assert (await s.scalar(select(Conversa))).status == "agente"


async def test_destino_de_handoff_na_criacao_e_na_edicao(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    assert agente["handoff_destino"] is None
    caminho = f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}"

    resp = await http.patch(caminho, json={"handoff_destino": {"tipo": "time", "id": 2, "nome": "Vendas"}}, headers=ADMIN)
    assert resp.status_code == 200, resp.text
    assert resp.json()["handoff_destino"] == {"tipo": "time", "id": 2, "nome": "Vendas"}

    resp = await http.patch(caminho, json={"handoff_destino": {"tipo": "usuario"}}, headers=ADMIN)
    assert resp.status_code == 422

    outro = await cria_cliente_e_agente(http, "Padaria", "Bia")
    resp = await http.patch(f"/admin/clientes/{outro['cliente_id']}/agentes/{agente['id']}", json={"handoff_destino": None}, headers=ADMIN)
    assert resp.status_code == 404

    cliente = (await http.post("/admin/clientes", json={"nome": "Mercado"}, headers=ADMIN)).json()
    resp = await http.post(
        f"/admin/clientes/{cliente['id']}/agentes",
        json={"nome": "Leo", "canal": "chatwoot", "conexao": {"url": "https://chatwoot.exemplo.com.br", "token_admin": "x", "account_id": 1, "inbox_ids": [3]}, "handoff_destino": {"tipo": "grupo"}},
        headers=ADMIN,
    )
    assert resp.status_code == 422
    assert canal.desconectados == []


async def test_handoff_de_um_cliente_nao_aparece_em_outro(http, canal, fila, sessao, redis, modelo) -> None:  # type: ignore[no-untyped-def]
    from app.handoff import repo

    await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    ana = (await http.get("/admin/agentes", headers=ADMIN)).json()[0]
    await envia_webhook(http, ana["url_webhook"].rsplit("/", 1)[1], payload_chatwoot(conteudo="quero falar com uma pessoa"))
    assert await _turno(sessao, redis) == "transferido"

    async with sessao() as s:
        conversa = await s.scalar(select(Conversa))
        assert await repo.aberto(s, conversa.cliente_id, conversa.id) is not None
        assert await repo.aberto(s, uuid.uuid4(), conversa.id) is None
        assert not await repo.fecha(s, uuid.uuid4(), conversa.id, "chatwoot")


async def test_depois_da_devolucao_o_modelo_ve_que_o_pedido_de_pessoa_ja_foi_atendido(http, canal, fila, sessao, redis, modelo, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    vistos: list[list[ModelMessage]] = []
    original = modelo.__call__

    def espia(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if e_resposta(info):
            vistos.append(list(historico))
        return original(historico, info)

    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(espia))
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=1, conteudo="quero falar com uma pessoa"))
    assert await _turno(sessao, redis) == "transferido"
    canal.status = "pending"
    await envia_webhook(http, agente["token"], _devolucao())

    modelo.transfere = False
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=2, conteudo="qual a cotação do dólar?"))
    assert await _turno(sessao, redis) == "respondido"

    # O FunctionModel entrega a parte de sistema como fala com o prefixo <system>, no ponto em que está.
    linha_do_tempo = [str(getattr(p, "content", "")) for m in vistos[-1] for p in m.parts]
    avisos = [i for i, f in enumerate(linha_do_tempo) if f.startswith("<system>")]
    pedido = linha_do_tempo.index("quero falar com uma pessoa")
    assert len(avisos) == 2 and pedido < avisos[0] < avisos[1] < len(linha_do_tempo) - 1
    assert "contato pediu para falar com uma pessoa" in linha_do_tempo[avisos[0]]
    assert "devolveu a conversa para você" in linha_do_tempo[avisos[1]]
    assert linha_do_tempo[-1] == "qual a cotação do dólar?"


async def test_tool_de_handoff_chamada_de_novo_no_mesmo_turno_nao_repete(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    retornos: list[str] = []

    def chama_duas_vezes(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if not e_resposta(info):
            return ModelResponse(parts=[TextPart(RESUMO)])
        ultima = historico[-1]
        voltas = [p for p in ultima.parts if isinstance(p, ToolReturnPart)] if isinstance(ultima, ModelRequest) else []
        retornos.extend(str(p.content) for p in voltas)
        if len(retornos) < 2:
            return ModelResponse(parts=[ToolCallPart("transferir_para_humano", {"motivo": f"pedido {len(retornos) + 1}"})])
        return resposta_falsa(info, ["Já chamei alguém"])

    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(chama_duas_vezes))
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot(conteudo="quero falar com uma pessoa"))

    assert await _turno(sessao, redis) == "transferido"
    assert "Transferência registrada" in retornos[0] and "já registrada" in retornos[1]
    [registro] = await _handoffs(sessao)
    assert registro.motivo == "pedido 1"


async def test_modelo_em_loop_para_no_teto_do_turno_sem_tentar_de_novo(http, canal, fila, sessao, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    chamadas: list[int] = []

    def em_loop(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        if not e_resposta(info):
            return ModelResponse(parts=[TextPart(RESUMO)])
        chamadas.append(1)
        return ModelResponse(parts=[ToolCallPart("transferir_para_humano", {"motivo": "de novo"})])

    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(em_loop))
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot(conteudo="oi"))

    assert await _turno(sessao, redis) == "falhou"
    assert len(chamadas) <= config().limite_chamadas_modelo_por_turno
    assert [t for _, t in canal.enviadas] == [handoff.MENSAGEM_DE_EXPECTATIVA]
    async with sessao() as s:
        registro = await s.scalar(select(Turno).where(Turno.funcao == "resposta"))
    assert registro is not None and "UsageLimitExceeded" in (registro.erro or "")
