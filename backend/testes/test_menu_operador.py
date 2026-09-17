"""Operações do menu do operador: editar, remover, consumo e retomada."""

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

import httpx
from sqlalchemy import select

from app.agentes.modelos import Agente
from app.consumo.modelos import Falha, Turno
from app.conversas import turno
from app.conversas.modelos import Conversa, Mensagem
from app.handoff.modelos import Handoff
from app.plataforma import cripto
from app.plataforma.banco import agora
from app.plataforma.config import config
from testes.conftest import ADMIN, cria_cliente_e_agente, envia_webhook, payload_chatwoot


def _caminho(agente: dict[str, Any], cliente_id: str | None = None) -> str:
    return f"/admin/clientes/{cliente_id or agente['cliente_id']}/agentes/{agente['id']}"


async def _remove(http: httpx.AsyncClient, agente: dict[str, Any], **corpo: Any) -> httpx.Response:
    return await http.request("DELETE", _caminho(agente), json={"confirmacao": agente["nome"], **corpo}, headers=ADMIN)


# ── Editar ────────────────────────────────────────────────────────────────


async def test_editar_troca_so_os_campos_enviados(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    resp = await http.patch(
        _caminho(agente),
        json={"nome": " Ana Paula ", "buffer_segundos": 3, "max_mensagens_por_resposta": 2, "modelo_auxiliar": "openai:gpt-5-mini", "modelo_fallback": None},
        headers=ADMIN,
    )

    assert resp.status_code == 200, resp.text
    editado = resp.json()
    assert editado["nome"] == "Ana Paula" and editado["slug"] == "ana"
    assert editado["arquivo_prompt"] == agente["arquivo_prompt"]
    assert (editado["buffer_segundos"], editado["max_mensagens_por_resposta"]) == (3, 2)
    assert editado["modelo_auxiliar"] == "openai:gpt-5-mini" and editado["modelo_fallback"] is None
    assert editado["modelo_conversa"] == agente["modelo_conversa"]
    assert editado["url_webhook"] == agente["url_webhook"]


async def test_buffer_novo_vale_na_proxima_mensagem(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=1))

    await http.patch(_caminho(agente), json={"buffer_segundos": 20}, headers=ADMIN)
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=2))

    assert fila.adiamentos == [8, 20]


async def test_editar_recusa_valor_invalido(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    for corpo, trecho in (
        ({"modelo_conversa": "anthropic:claude-sonnet-5"}, "anthropic"),
        ({"modelo_transcricao": "openai"}, "provedor:modelo"),
        ({"modelo_conversa": None}, "vazios"),
        ({"nome": "   "}, "vazio"),
        ({"buffer_segundos": 0}, None),
        ({"retomada_automatica_horas": 4}, "devolve a conversa"),
        ({"canal": "telegram"}, None),
        ({"credenciais_cifradas": "x"}, None),
    ):
        resp = await http.patch(_caminho(agente), json=corpo, headers=ADMIN)
        assert resp.status_code == 422, corpo
        if trecho:
            assert trecho in str(resp.json()["detail"]), resp.text

    atual = (await http.get(_caminho(agente), headers=ADMIN)).json()
    assert {k: atual[k] for k in ("nome", "modelo_conversa", "buffer_segundos")} == {"nome": "Ana", "modelo_conversa": "openai:gpt-5.5", "buffer_segundos": 8}


async def test_rotas_admin_com_agente_de_outro_cliente_devolvem_404(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    bia = await cria_cliente_e_agente(http, "Padaria Pão Quente", "Bia")
    alheio = _caminho(ana, bia["cliente_id"])

    assert (await http.patch(alheio, json={"buffer_segundos": 3}, headers=ADMIN)).status_code == 404
    assert (await http.request("DELETE", alheio, json={"confirmacao": "Ana"}, headers=ADMIN)).status_code == 404
    assert (await http.get(_caminho(ana), headers=ADMIN)).json()["buffer_segundos"] == 8


# ── Remover ───────────────────────────────────────────────────────────────


async def test_remover_exige_o_nome_do_agente(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    resp = await http.request("DELETE", _caminho(agente), json={"confirmacao": "Bia"}, headers=ADMIN)

    assert resp.status_code == 422 and "Ana" in resp.json()["detail"]
    assert (await http.get(_caminho(agente), headers=ADMIN)).status_code == 200


async def test_agente_removido_para_de_responder_e_perde_credenciais(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=1))

    resp = await _remove(http, agente)

    assert resp.status_code == 200 and resp.json() == {"removido": True, "canal_desconectado": False}
    assert (await http.get(_caminho(agente), headers=ADMIN)).status_code == 404
    assert (await http.get("/admin/agentes", headers=ADMIN)).json() == []

    fila.jobs.clear()
    resp = await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=2, conteudo="ainda aí?"))
    assert resp.status_code == 200
    assert fila.jobs == []

    async with sessao() as s:
        assert [m.texto for m in await s.scalars(select(Mensagem))] == ["oi"]
        assert "webhook_token_desconhecido" in set(await s.scalars(select(Falha.tipo)))
        linha = (await s.execute(select(Conversa.cliente_id, Conversa.id))).one()
        cifradas = await s.scalar(select(Agente.credenciais_cifradas))
    assert cripto.decifra(cifradas) == {}

    # Job do buffer agendado antes da remoção não responde.
    assert await turno._turno(linha.cliente_id, linha.id, _sempre) == "agente_inativo"
    assert canal.enviadas == []


async def _sempre() -> bool:
    return True


async def test_renomear_leva_o_nome_ao_canal_so_com_acesso(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Samuelson")

    await http.patch(_caminho(agente), json={"nome": "Tico"}, headers=ADMIN)
    assert canal.renomeados == []

    canal.desconectar_recusa = True
    resp = await http.patch(_caminho(agente), json={"nome": "Ticotico", "conexao": {"token_admin": "de-atendente"}}, headers=ADMIN)
    assert resp.status_code == 422
    assert (await http.get(_caminho(agente), headers=ADMIN)).json()["nome"] == "Tico"

    canal.desconectar_recusa = False
    resp = await http.patch(_caminho(agente), json={"nome": "Ticotico", "conexao": {"token_admin": "de-admin"}}, headers=ADMIN)
    assert resp.status_code == 200 and resp.json()["nome"] == "Ticotico"
    assert canal.renomeados == ["Ticotico"]


async def test_remover_agente_renomeado_aceita_o_nome_atual(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Samuelson")
    await http.patch(_caminho(agente), json={"nome": "Ticotico"}, headers=ADMIN)

    resp = await http.request("DELETE", _caminho(agente), json={"confirmacao": "ticotico"}, headers=ADMIN)

    assert resp.status_code == 200, resp.text


async def test_remover_com_acesso_apaga_o_bot_e_recusa_nao_remove(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    canal.desconectar_recusa = True
    resp = await _remove(http, agente, conexao={"token_admin": "de-atendente"})
    assert resp.status_code == 422 and "administrador" in resp.json()["detail"]
    assert (await http.get(_caminho(agente), headers=ADMIN)).status_code == 200

    canal.desconectar_recusa = False
    resp = await _remove(http, agente, conexao={"token_admin": "de-admin"})
    assert resp.json() == {"removido": True, "canal_desconectado": True}
    assert canal.desconectados == [42]


async def test_agente_novo_com_o_mesmo_nome_reaproveita_o_prompt(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    persona = config().diretorio_prompts / agente["arquivo_prompt"]
    persona.write_text("persona editada pelo operador", encoding="utf-8")
    await _remove(http, agente)

    resp = await http.post(
        f"/admin/clientes/{agente['cliente_id']}/agentes",
        json={"nome": "Ana", "canal": "chatwoot", "conexao": {"url": "https://chatwoot.exemplo.com.br", "token_admin": "x", "account_id": 1, "inbox_ids": [3]}},
        headers=ADMIN,
    )

    assert resp.status_code == 201, resp.text
    assert resp.json()["arquivo_prompt"] == agente["arquivo_prompt"]
    assert persona.read_text(encoding="utf-8") == "persona editada pelo operador"


async def test_empresa_so_sai_sem_agentes_e_o_nome_fica_livre(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    empresa = f"/admin/clientes/{agente['cliente_id']}"

    assert (await http.request("DELETE", empresa, json={"confirmacao": "Loja Exemplo"}, headers=ADMIN)).status_code == 409
    await _remove(http, agente)
    assert (await http.request("DELETE", empresa, json={"confirmacao": "Padaria"}, headers=ADMIN)).status_code == 422
    assert (await http.request("DELETE", empresa, json={"confirmacao": "loja exemplo"}, headers=ADMIN)).status_code == 204

    assert (await http.get("/admin/clientes", headers=ADMIN)).json() == []
    assert (await http.post("/admin/clientes", json={"nome": "Loja Exemplo"}, headers=ADMIN)).status_code == 201
    assert (await http.request("DELETE", empresa, json={"confirmacao": "Loja Exemplo"}, headers=ADMIN)).status_code == 404


# ── Consumo e falhas ──────────────────────────────────────────────────────


async def _turnos(sessao: Any, conversa_por_cliente: dict[uuid.UUID, uuid.UUID], **campos: Any) -> None:
    async with sessao() as s:
        for cliente_id, conversa_id in conversa_por_cliente.items():
            s.add(Turno(cliente_id=cliente_id, conversa_id=conversa_id, modelo="openai:gpt-5.5", **campos))
        await s.commit()


async def test_consumo_filtrado_por_cliente_e_periodo(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    bia = await cria_cliente_e_agente(http, "Padaria Pão Quente", "Bia")
    await envia_webhook(http, ana["token"], payload_chatwoot(mensagem_id=1, conversa=10))
    await envia_webhook(http, bia["token"], payload_chatwoot(mensagem_id=2, conversa=10))
    async with sessao() as s:
        conversas = {c.cliente_id: c.id for c in await s.scalars(select(Conversa))}
    loja = uuid.UUID(ana["cliente_id"])

    await _turnos(sessao, conversas, tokens_entrada=1000, tokens_saida=100, custo_estimado=Decimal("0.01"))
    await _turnos(sessao, {loja: conversas[loja]}, funcao="transcricao", tokens_entrada=50, custo_estimado=None)
    await _turnos(sessao, {loja: conversas[loja]}, tokens_entrada=99999, criado_em=agora() - timedelta(days=10))
    async with sessao() as s:
        s.add(Falha(tipo="envio_falhou", detalhe={"erro": "HTTP 500"}, cliente_id=loja, agente_id=uuid.UUID(ana["id"])))
        s.add(Falha(tipo="webhook_assinatura_invalida", detalhe={}, cliente_id=uuid.UUID(bia["cliente_id"])))
        await s.commit()

    resp = await http.get("/admin/consumo", params={"cliente_id": ana["cliente_id"], "dias": 7}, headers=ADMIN)

    assert resp.status_code == 200, resp.text
    [linha] = resp.json()["agentes"]
    assert (linha["cliente"], linha["agente"], linha["turnos"], linha["chamadas"]) == ("Loja Exemplo", "Ana", 1, 2)
    assert (linha["tokens_entrada"], linha["tokens_saida"], linha["sem_custo"]) == (1050, 100, 1)
    assert Decimal(linha["custo_estimado"]) == Decimal("0.01")
    assert [f["tipo"] for f in resp.json()["falhas"]] == ["envio_falhou"]
    assert resp.json()["falhas"][0]["agente"] == "Ana"

    todos = (await http.get("/admin/consumo", params={"dias": 30}, headers=ADMIN)).json()
    assert [(a["cliente"], a["tokens_entrada"]) for a in todos["agentes"]] == [("Loja Exemplo", 101049), ("Padaria Pão Quente", 1000)]
    assert len(todos["falhas"]) == 2

    so_bia = await http.get("/admin/consumo", params={"cliente_id": bia["cliente_id"], "agente_id": ana["id"]}, headers=ADMIN)
    assert so_bia.json()["agentes"] == []


async def test_consumo_valida_filtros(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    assert (await http.get("/admin/consumo", params={"agente_id": ana["id"]}, headers=ADMIN)).status_code == 422
    assert (await http.get("/admin/consumo", params={"cliente_id": str(uuid.uuid4())}, headers=ADMIN)).status_code == 404
    assert (await http.get("/admin/consumo", params={"dias": 0}, headers=ADMIN)).status_code == 422
    assert (await http.get("/admin/consumo")).status_code == 401


# ── Retomar ───────────────────────────────────────────────────────────────


async def test_operador_retoma_conversa_com_handoff_aberto(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    bia = await cria_cliente_e_agente(http, "Padaria Pão Quente", "Bia")
    await envia_webhook(http, ana["token"], payload_chatwoot(conversa=1532))
    async with sessao() as s:
        conversa = await s.scalar(select(Conversa))
        s.add(Handoff(cliente_id=conversa.cliente_id, agente_id=conversa.agente_id, conversa_id=conversa.id, motivo="pediu humano", resumo="r", codigo="ABC234"))
        conversa.status = "humano"
        await s.commit()
    caminho = f"/conversas/{conversa.id}/retomar"

    assert (await http.post(f"/admin/clientes/{bia['cliente_id']}{caminho}", headers=ADMIN)).status_code == 404
    assert canal.devolvidas == []

    resp = await http.post(f"/admin/clientes/{ana['cliente_id']}{caminho}", headers=ADMIN)
    assert resp.status_code == 200 and resp.json() == {"retomado": True}
    assert canal.devolvidas == ["1532"]
    async with sessao() as s:
        handoff = await s.scalar(select(Handoff))
        assert (handoff.retomado_por, (await s.scalar(select(Conversa))).status) == ("operador", "agente")

    assert (await http.post(f"/admin/clientes/{ana['cliente_id']}{caminho}", headers=ADMIN)).json() == {"retomado": False}
