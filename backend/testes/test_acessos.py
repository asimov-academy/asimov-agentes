"""Token de administrador do Chatwoot: pedido uma vez, guardado cifrado e reaproveitado."""

from sqlalchemy import select

from app.acessos.modelos import AcessoCanal
from testes.conftest import ADMIN, CONEXAO_EXEMPLO, TOKEN_ADMIN, cria_cliente_e_agente

SEM_TOKEN = {k: v for k, v in CONEXAO_EXEMPLO.items() if k != "token_admin"}
URL = "https://chatwoot.exemplo.com.br"


async def _descobre(http, conexao):  # type: ignore[no-untyped-def]
    return await http.post("/admin/canais/chatwoot/descobrir", json={"conexao": conexao}, headers=ADMIN)


async def test_sem_token_guardado_a_api_pede_o_token(http, canal) -> None:  # type: ignore[no-untyped-def]
    resp = await _descobre(http, {"url": URL})
    assert resp.status_code == 428 and "token" in resp.json()["detail"]


async def test_token_informado_fica_guardado_cifrado_e_vale_depois(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    assert (await _descobre(http, {"url": URL + "/", "token_admin": TOKEN_ADMIN})).status_code == 200

    assert (await _descobre(http, {"url": URL})).status_code == 200
    cliente = (await http.post("/admin/clientes", json={"nome": "Loja"}, headers=ADMIN)).json()
    resp = await http.post(
        f"/admin/clientes/{cliente['id']}/agentes",
        json={"nome": "Ana", "canal": "chatwoot", "conexao": SEM_TOKEN},
        headers=ADMIN,
    )
    assert resp.status_code == 201, resp.text
    assert canal.tokens_usados == [TOKEN_ADMIN, TOKEN_ADMIN, TOKEN_ADMIN]

    async with sessao() as s:
        [guardado] = list(await s.scalars(select(AcessoCanal)))
    assert guardado.endereco == URL and TOKEN_ADMIN not in guardado.acesso_cifrado
    listagem = await http.get("/admin/canais/chatwoot/acessos", headers=ADMIN)
    assert [a["endereco"] for a in listagem.json()] == [URL] and TOKEN_ADMIN not in listagem.text


async def test_token_recusado_nao_fica_guardado_e_guardado_recusado_e_apagado(http, canal, sessao) -> None:  # type: ignore[no-untyped-def]
    resp = await _descobre(http, {"url": URL, "token_admin": "de-atendente"})
    assert resp.status_code == 428 and "administrador" in resp.json()["detail"]
    async with sessao() as s:
        assert list(await s.scalars(select(AcessoCanal))) == []

    await _descobre(http, {"url": URL, "token_admin": TOKEN_ADMIN})
    canal.desconectar_recusa = True
    assert (await _descobre(http, {"url": URL})).status_code == 428
    canal.desconectar_recusa = False
    assert (await _descobre(http, {"url": URL})).status_code == 428, "token recusado não pode continuar guardado"


async def test_esquecer_o_token(http, canal) -> None:  # type: ignore[no-untyped-def]
    await _descobre(http, {"url": URL, "token_admin": TOKEN_ADMIN})

    resp = await http.request("DELETE", "/admin/canais/chatwoot/acessos", params={"endereco": URL + "/"}, headers=ADMIN)
    assert resp.status_code == 204
    assert (await _descobre(http, {"url": URL})).status_code == 428
    resp = await http.request("DELETE", "/admin/canais/chatwoot/acessos", params={"endereco": URL}, headers=ADMIN)
    assert resp.status_code == 404


async def test_criar_agente_sem_token_guardado_nao_conecta(http, canal) -> None:  # type: ignore[no-untyped-def]
    cliente = (await http.post("/admin/clientes", json={"nome": "Loja"}, headers=ADMIN)).json()
    resp = await http.post(
        f"/admin/clientes/{cliente['id']}/agentes",
        json={"nome": "Ana", "canal": "chatwoot", "conexao": SEM_TOKEN},
        headers=ADMIN,
    )
    assert resp.status_code == 428
    assert canal.tokens_usados == []
    assert await cria_cliente_e_agente(http, "Padaria", "Bia")
