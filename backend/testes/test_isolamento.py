import uuid

from sqlalchemy import select

from app.agentes import repo as agentes_repo
from app.conversas import repo as conversas_repo
from app.conversas.modelos import Conversa, Mensagem
from testes.conftest import ADMIN, cria_cliente_e_agente, envia_webhook, payload_chatwoot


async def _dois_clientes_com_conversa(http):  # type: ignore[no-untyped-def]
    a = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    b = await cria_cliente_e_agente(http, "Padaria Pão Quente", "Bia")
    await envia_webhook(http, a["token"], payload_chatwoot(mensagem_id=1, conversa=10, conteudo="segredo da Loja Exemplo"))
    await envia_webhook(http, b["token"], payload_chatwoot(mensagem_id=2, conversa=10, conteudo="pedido da padaria"))
    return a, b


async def test_repositorios_nunca_devolvem_dado_de_outro_cliente(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    a, b = await _dois_clientes_com_conversa(http)
    cliente_a, cliente_b = uuid.UUID(a["cliente_id"]), uuid.UUID(b["cliente_id"])

    async with sessao() as s:
        conversa_a = await s.scalar(select(Conversa).where(Conversa.cliente_id == cliente_a))
        assert conversa_a is not None

        assert await conversas_repo.obter_conversa(s, cliente_b, conversa_a.id) is None
        assert await conversas_repo.ultimas_mensagens(s, cliente_b, conversa_a.id) == []
        assert await conversas_repo.conversa_por_externo(s, cliente_b, uuid.UUID(a["id"]), "10") is None
        assert await agentes_repo.obter(s, cliente_b, uuid.UUID(a["id"])) is None
        assert [ag.nome for ag in await agentes_repo.listar(s, cliente_b)] == ["Bia"]

        textos_a = [m.texto for m in await conversas_repo.ultimas_mensagens(s, cliente_a, conversa_a.id)]
        assert textos_a == ["segredo da Loja Exemplo"]


async def test_mesma_conversa_externa_em_clientes_diferentes_nao_se_mistura(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    await _dois_clientes_com_conversa(http)

    async with sessao() as s:
        conversas = list(await s.scalars(select(Conversa)))
        mensagens = list(await s.scalars(select(Mensagem)))

    assert len(conversas) == 2
    assert {c.cliente_id for c in conversas} == {m.cliente_id for m in mensagens}
    for m in mensagens:
        dona = next(c for c in conversas if c.id == m.conversa_id)
        assert dona.cliente_id == m.cliente_id


async def test_rota_admin_com_agente_de_outro_cliente_devolve_404(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    a, b = await _dois_clientes_com_conversa(http)

    resp = await http.get(f"/admin/clientes/{b['cliente_id']}/agentes/{a['id']}", headers=ADMIN)
    assert resp.status_code == 404

    resp = await http.get(f"/admin/clientes/{a['cliente_id']}/agentes/{a['id']}", headers=ADMIN)
    assert resp.status_code == 200


async def test_listagem_filtrada_por_cliente(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    a, b = await _dois_clientes_com_conversa(http)

    resp = await http.get("/admin/agentes", params={"cliente_id": a["cliente_id"]}, headers=ADMIN)
    assert [ag["nome"] for ag in resp.json()] == ["Ana"]
