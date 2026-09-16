import httpx
from sqlalchemy import text

from app.main import app

from app.plataforma.cripto import decifra

from testes.conftest import ADMIN, BOT_SECRET, CONEXAO_EXEMPLO, TOKEN_ADMIN, TOKEN_BOT, cria_cliente_e_agente, envia_webhook, payload_chatwoot


async def test_admin_exige_chave(http) -> None:  # type: ignore[no-untyped-def]
    assert (await http.get("/admin/clientes")).status_code == 401
    assert (await http.get("/admin/clientes", headers={"X-Admin-Key": "errada"})).status_code == 401
    assert (await http.get("/admin/clientes", headers=ADMIN)).status_code == 200


async def test_cliente_repetido_devolve_409(http) -> None:  # type: ignore[no-untyped-def]
    assert (await http.post("/admin/clientes", json={"nome": "Loja Exemplo"}, headers=ADMIN)).status_code == 201
    assert (await http.post("/admin/clientes", json={"nome": "Loja  exemplo"}, headers=ADMIN)).status_code == 409


async def test_agente_com_modelo_sem_chave_devolve_422(http, canal) -> None:  # type: ignore[no-untyped-def]
    cliente = (await http.post("/admin/clientes", json={"nome": "Loja"}, headers=ADMIN)).json()
    resp = await http.post(
        f"/admin/clientes/{cliente['id']}/agentes",
        json={
            "nome": "Ana",
            "canal": "chatwoot",
            "conexao": CONEXAO_EXEMPLO,
            "modelos": {"modelo_conversa": "anthropic:claude-sonnet-5"},
        },
        headers=ADMIN,
    )
    assert resp.status_code == 422
    assert "anthropic" in resp.json()["detail"]


async def test_agente_cria_prompts_e_usa_padroes_do_provedor(http, canal) -> None:  # type: ignore[no-untyped-def]
    from app.plataforma.config import config

    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    assert agente["modelo_conversa"] == "openai:gpt-5.5"
    assert agente["url_webhook"].startswith("https://bot.teste.local/webhook/chatwoot/")
    persona = (config().diretorio_prompts / agente["arquivo_prompt"]).read_text()
    assert "Ana" in persona and "Loja Exemplo" in persona


async def test_credenciais_nunca_saem_em_claro(http, canal, fila, sessao, capsys) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot())
    listagem = await http.get("/admin/agentes", headers=ADMIN)

    for texto in (listagem.text, str(agente), capsys.readouterr().out):
        for segredo in (TOKEN_BOT, BOT_SECRET, TOKEN_ADMIN):
            assert segredo not in texto

    async with sessao() as s:
        linha = (await s.execute(text("select credenciais_cifradas, token_webhook_hash from agente"))).one()
    for segredo in (TOKEN_BOT, BOT_SECRET, TOKEN_ADMIN):
        assert segredo not in linha[0]
    assert agente["token"] not in linha[1]
    assert TOKEN_ADMIN not in str(decifra(linha[0])), "token do administrador não pode ser guardado"


async def test_falha_ao_gravar_desfaz_conexao_no_canal(http, canal, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.agentes import servico

    def quebra(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise OSError("disco cheio")

    monkeypatch.setattr(servico, "_cria_prompts", quebra)
    cliente = (await http.post("/admin/clientes", json={"nome": "Loja"}, headers=ADMIN)).json()
    transporte = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transporte, base_url="http://teste") as sem_excecao:
        resp = await sem_excecao.post(
            f"/admin/clientes/{cliente['id']}/agentes",
            json={"nome": "Ana", "canal": "chatwoot", "conexao": CONEXAO_EXEMPLO},
            headers=ADMIN,
        )
    assert resp.status_code == 500
    assert "OSError: disco cheio" in resp.json()["detail"]
    assert canal.desconectados == [42]
    assert (await http.get("/admin/agentes", headers=ADMIN)).json() == []
