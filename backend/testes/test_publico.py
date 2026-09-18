"""Página pública de privacidade: a URL que a Meta exige para publicar o app.

É a única rota do projeto que devolve HTML, e a única fora de `/admin` e `/webhook` que o Caddy
publica. Nada sensível pode sair por ela.
"""

import httpx

from testes.conftest import ADMIN


async def test_privacidade_da_instalacao_responde_html_com_o_dominio(http) -> None:  # type: ignore[no-untyped-def]
    resp = await http.get("/privacidade")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/html")
    assert "bot.teste.local" in resp.text
    assert "Política de privacidade" in resp.text


async def test_privacidade_da_empresa_leva_o_nome_dela(http: httpx.AsyncClient) -> None:
    await http.post("/admin/clientes", json={"nome": "Loja Exemplo"}, headers=ADMIN)

    resp = await http.get("/privacidade/loja-exemplo")

    assert resp.status_code == 200 and "Loja Exemplo" in resp.text


async def test_empresa_que_nao_existe_responde_404(http) -> None:  # type: ignore[no-untyped-def]
    """Sem listagem e sem pista: quem não sabe o slug não descobre os clientes da instalação."""
    resp = await http.get("/privacidade/nao-existe")

    assert resp.status_code == 404


async def test_empresa_removida_sai_do_ar(http: httpx.AsyncClient) -> None:
    cliente = (await http.post("/admin/clientes", json={"nome": "Saiu"}, headers=ADMIN)).json()
    await http.request(
        "DELETE",
        f"/admin/clientes/{cliente['id']}",
        json={"confirmacao": "Saiu"},
        headers=ADMIN,
    )

    assert (await http.get("/privacidade/saiu")).status_code == 404


async def test_privacidade_do_agente_leva_empresa_e_agente(http, canal) -> None:  # type: ignore[no-untyped-def]
    """Na Meta é um app por número, e cada app quer a própria URL."""
    from testes.conftest import cria_cliente_e_agente

    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    resp = await http.get("/privacidade/loja-exemplo/ana")

    assert resp.status_code == 200
    assert "Loja Exemplo" in resp.text and "atendimento de Ana" in resp.text
    # A API diz a URL, para o menu mostrar sem ter de montar o endereço.
    assert agente["url_privacidade"] == "https://bot.teste.local/privacidade/loja-exemplo/ana"


async def test_agente_de_outra_empresa_nao_aparece_na_url_dela(http, canal) -> None:  # type: ignore[no-untyped-def]
    from testes.conftest import cria_cliente_e_agente

    await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await http.post("/admin/clientes", json={"nome": "Outra"}, headers=ADMIN)

    assert (await http.get("/privacidade/outra/ana")).status_code == 404
