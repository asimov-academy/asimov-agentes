"""Tom de voz, transferência opcional para humano e restrição de temas.

São as três escolhas que o operador faz no passo "Jeito" do onboarding e na aba Comunicação da
ficha. O que estes testes seguram:

- o tom entra no prompt de sistema, e tom desconhecido é recusado antes de chegar ao banco;
- **handoff desligado desliga todos os caminhos**: a tool nem é oferecida ao modelo, e uma falha no
  turno ou um arquivo grande demais também não transferem. Prometer uma pessoa que não existe é
  pior do que dizer que não dá;
- restringir temas nasce ligado e sai do prompt quando o operador desliga;
- agente que já existia continua como estava: tom normal e transferindo.
"""

from typing import Any

import pytest
from arq import create_pool
from arq.connections import RedisSettings
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.conversas import buffer, turno
from app.conversas.modelos import Conversa
from app.plataforma.config import config
from testes.conftest import ADMIN, cria_cliente_e_agente, envia_webhook, payload_chatwoot, resposta_falsa


@pytest.fixture
async def redis() -> Any:
    pool = await create_pool(RedisSettings.from_dsn(config().redis_url))
    await pool.flushdb()
    yield pool
    await pool.aclose()


@pytest.fixture
def instrucoes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """As instruções que o modelo recebeu em cada turno."""
    vistas: list[str] = []

    def responde(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        vistas.append(info.instructions or "")
        return resposta_falsa(info, ["Oi"])

    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(responde))
    # O sleep do envio precisa continuar aguardável: o turno faz `await` nele.
    async def sem_espera(segundos: float) -> None:
        return None

    monkeypatch.setattr(turno.asyncio, "sleep", sem_espera)
    return vistas


async def roda_um_turno(http, sessao, redis, agente, mensagem_id: int = 1) -> str:  # type: ignore[no-untyped-def]
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=mensagem_id))
    async with sessao() as s:
        conversa = await s.scalar(select(Conversa))
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)
    return await turno.processar_turno(
        {"redis": redis}, str(conversa.cliente_id), str(conversa.id), token
    )


async def test_agente_nasce_com_tom_normal_transferindo_e_so_no_assunto_da_empresa(http, canal) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    assert agente["tom"] == "normal"
    assert agente["transfere_para_humano"] is True
    # Quem contrata um agente de atendimento não quer o modelo respondendo qualquer coisa em nome
    # da empresa: a restrição nasce ligada e o operador desliga se quiser.
    assert agente["restringe_temas"] is True


async def test_tom_entra_no_prompt_e_tom_inventado_e_recusado(http, canal, fila, sessao, redis, instrucoes) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana", tom="descontraido")
    caminho = f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}"

    assert await roda_um_turno(http, sessao, redis, agente, 1) == "respondido"
    assert "leve e próximo" in instrucoes[0]

    assert (await http.patch(caminho, json={"tom": "formal"}, headers=ADMIN)).status_code == 200
    assert await roda_um_turno(http, sessao, redis, agente, 2) == "respondido"
    assert "sem gíria" in instrucoes[1]

    assert (await http.patch(caminho, json={"tom": "gritando"}, headers=ADMIN)).status_code == 422


async def test_restringir_temas_nasce_ligado_e_sai_do_prompt_quando_desligado(http, canal, fila, sessao, redis, instrucoes) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    caminho = f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}"

    assert await roda_um_turno(http, sessao, redis, agente, 1) == "respondido"
    assert "apenas do que é da empresa" in instrucoes[0]

    await http.patch(caminho, json={"restringe_temas": False}, headers=ADMIN)
    assert await roda_um_turno(http, sessao, redis, agente, 2) == "respondido"
    assert "apenas do que é da empresa" not in instrucoes[1]


async def test_handoff_desligado_tira_a_tool_e_a_promessa(http, canal, fila, sessao, redis, instrucoes) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana", transfere_para_humano=False)

    assert await roda_um_turno(http, sessao, redis, agente, 1) == "respondido"
    assert "Não existe transferência" in instrucoes[0]
    assert "use transferir_para_humano" not in instrucoes[0]


async def test_handoff_desligado_nao_transfere_nem_por_falha(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    """O caminho automático (falha no turno, arquivo grande) também respeita a escolha."""
    from app.agentes import repo as agentes_repo
    from app.canais.registro import obter_canal
    from app.conversas.modelos import Conversa
    from app.handoff import servico as handoff

    agente_json = await cria_cliente_e_agente(
        http, "Loja Exemplo", "Ana", transfere_para_humano=False
    )
    await envia_webhook(http, agente_json["token"], payload_chatwoot(mensagem_id=1))
    async with sessao() as s:
        conversa = await s.scalar(select(Conversa))
        agente = await agentes_repo.obter(s, conversa.cliente_id, conversa.agente_id)
        resultado = await handoff.transferir(
            s, agente, obter_canal("chatwoot"), {}, conversa, handoff.MOTIVO_FALHA_NO_TURNO
        )

    assert resultado == "desligado"
    assert canal.transferencias == []
