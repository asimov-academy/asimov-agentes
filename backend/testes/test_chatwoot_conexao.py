"""Conexão com a API do Chatwoot simulada no nível HTTP, com as rotas e respostas do código do Chatwoot."""

import json
from typing import Any

import httpx
import pytest

from app.canais.base import CredencialInvalida
from app.canais.chatwoot.canal import Chatwoot

URL = "https://chatwoot.exemplo.com.br"
ADMIN = "token-admin"
WEBHOOK = "https://bot.teste.local/webhook/chatwoot/abc"


class ChatwootHttp(Chatwoot):
    def __init__(self, responde: Any) -> None:
        self.chamadas: list[tuple[str, str, dict[str, Any] | None]] = []

        def transporte(req: httpx.Request) -> httpx.Response:
            corpo = json.loads(req.content) if req.content else None
            self.chamadas.append((req.method, req.url.path, corpo))
            assert req.headers.get("api_access_token")
            return responde(req, corpo)

        self._transporte = httpx.MockTransport(transporte)

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(transport=self._transporte)


def chatwoot_real(req: httpx.Request, corpo: Any, set_agent_bot_status: int = 200, criar_status: int = 200) -> httpx.Response:
    caminho, metodo = req.url.path, req.method
    if caminho == "/api/v1/profile":
        if req.headers["api_access_token"] != ADMIN:
            return httpx.Response(401, json={"error": "Invalid Access Token"})
        return httpx.Response(200, json={"id": 7, "accounts": [{"id": 1, "name": "Loja Exemplo"}]})
    if caminho == "/api/v1/accounts/1/inboxes":
        return httpx.Response(200, json={"payload": [{"id": 3, "name": "WhatsApp", "channel_type": "Channel::Whatsapp"}]})
    if caminho == "/api/v1/accounts/1/agents":
        return httpx.Response(200, json=[{"id": 7, "name": "Joana", "email": "joana@exemplo.com.br", "role": "administrator"}])
    if caminho == "/api/v1/accounts/1/teams":
        return httpx.Response(404, json={"error": "feature disabled"})
    if caminho == "/api/v1/accounts/1/agent_bots" and metodo == "POST":
        if criar_status != 200:
            return httpx.Response(criar_status, json={"error": "unauthorized"})
        return httpx.Response(200, json={"id": 99, "name": corpo["name"], "outgoing_url": corpo["outgoing_url"], "access_token": "tok-bot", "secret": "seg-bot"})
    if caminho == "/api/v1/accounts/1/inboxes/3/set_agent_bot":
        return httpx.Response(set_agent_bot_status)
    if caminho == "/api/v1/accounts/1/agent_bots/99" and metodo == "DELETE":
        return httpx.Response(200)
    return httpx.Response(404)


CONEXAO = {"url": URL + "/", "token_admin": ADMIN, "account_id": 1, "inbox_ids": [3]}


async def test_descobrir_lista_contas_e_caixas() -> None:
    canal = ChatwootHttp(chatwoot_real)
    resultado = await canal.descobrir({"url": URL, "token_admin": ADMIN})
    assert resultado == {
        "contas": [
            {
                "id": 1,
                "nome": "Loja Exemplo",
                "caixas": [{"id": 3, "nome": "WhatsApp", "tipo": "Channel::Whatsapp"}],
                "atendentes": [{"id": 7, "nome": "Joana"}],
                "times": [],
            }
        ]
    }


async def test_descobrir_com_token_errado() -> None:
    canal = ChatwootHttp(chatwoot_real)
    with pytest.raises(CredencialInvalida, match="token recusado"):
        await canal.descobrir({"url": URL, "token_admin": "errado"})


async def test_conectar_cria_bot_com_webhook_liga_na_caixa_e_nao_guarda_admin() -> None:
    canal = ChatwootHttp(chatwoot_real)

    credenciais = await canal.conectar(CONEXAO, WEBHOOK, "Ana")

    assert ("POST", "/api/v1/accounts/1/agent_bots", {"name": "Ana", "description": "Criado pelo setup Asimov Academy", "outgoing_url": WEBHOOK}) in canal.chamadas
    assert ("POST", "/api/v1/accounts/1/inboxes/3/set_agent_bot", {"agent_bot": 99}) in canal.chamadas
    assert credenciais == {"url": URL, "account_id": 1, "inbox_ids": [3], "api_access_token": "tok-bot", "bot_id": 99, "bot_secret": "seg-bot"}
    assert ADMIN not in str(credenciais)


async def test_conectar_sem_ser_administrador() -> None:
    canal = ChatwootHttp(lambda req, corpo: chatwoot_real(req, corpo, criar_status=401))
    with pytest.raises(CredencialInvalida, match="administrador"):
        await canal.conectar(CONEXAO, WEBHOOK, "Ana")


async def test_falha_ao_ligar_na_caixa_apaga_o_bot_criado() -> None:
    canal = ChatwootHttp(lambda req, corpo: chatwoot_real(req, corpo, set_agent_bot_status=404))
    with pytest.raises(CredencialInvalida, match="caixa de entrada 3"):
        await canal.conectar(CONEXAO, WEBHOOK, "Ana")
    assert ("DELETE", "/api/v1/accounts/1/agent_bots/99", None) in canal.chamadas


async def test_operacao_usa_token_do_bot() -> None:
    canal = ChatwootHttp(lambda req, corpo: httpx.Response(200, json={"status": "pending", "id": 5}))
    credenciais = {"url": URL, "account_id": 1, "inbox_ids": [3], "api_access_token": "tok-bot", "bot_id": 99, "bot_secret": "seg-bot"}

    assert await canal.agente_pode_falar(credenciais, "12")
    await canal.digitando(credenciais, "12", True)
    assert await canal.enviar_texto(credenciais, "12", "oi") == "5"
    assert [c[1] for c in canal.chamadas] == [
        "/api/v1/accounts/1/conversations/12",
        "/api/v1/accounts/1/conversations/12/toggle_typing_status",
        "/api/v1/accounts/1/conversations/12/messages",
    ]


CREDENCIAIS = {"url": URL, "account_id": 1, "inbox_ids": [3], "api_access_token": "tok-bot", "bot_id": 99, "bot_secret": "seg-bot"}


@pytest.mark.parametrize(
    ("destino", "atribuicao"),
    [
        ({"tipo": "usuario", "id": 7}, {"assignee_id": 7}),
        ({"tipo": "time", "id": 2}, {"team_id": 2}),
        ({"tipo": "caixa"}, None),
        (None, None),
    ],
)
async def test_transferir_nota_atribui_e_abre_nessa_ordem(destino, atribuicao) -> None:  # type: ignore[no-untyped-def]
    canal = ChatwootHttp(lambda req, corpo: httpx.Response(200, json={"id": 1}))

    problemas = await canal.transferir(CREDENCIAIS, "12", destino, "resumo")

    esperadas = [("POST", "/api/v1/accounts/1/conversations/12/messages", {"content": "resumo", "message_type": "outgoing", "private": True})]
    if atribuicao:
        esperadas.append(("POST", "/api/v1/accounts/1/conversations/12/assignments", atribuicao))
    esperadas.append(("POST", "/api/v1/accounts/1/conversations/12/toggle_status", {"status": "open"}))
    assert canal.chamadas == esperadas
    assert problemas == []


async def test_transferir_abre_mesmo_com_atribuicao_recusada_e_levanta_se_nao_abrir() -> None:
    def responde(req: httpx.Request, corpo: Any) -> httpx.Response:
        return httpx.Response(404 if req.url.path.endswith("assignments") else 200, json={})

    canal = ChatwootHttp(responde)
    assert await canal.transferir(CREDENCIAIS, "12", {"tipo": "usuario", "id": 7}, "resumo") == ["atribuição recusada: HTTP 404"]
    assert canal.chamadas[-1][1].endswith("toggle_status")

    canal = ChatwootHttp(lambda req, corpo: httpx.Response(401 if req.url.path.endswith("toggle_status") else 200, json={}))
    with pytest.raises(httpx.HTTPStatusError):
        await canal.transferir(CREDENCIAIS, "12", None, "resumo")


def test_destino_de_handoff_validado() -> None:
    from app.canais.base import DestinoInvalido

    canal = Chatwoot()
    assert canal.valida_destino_handoff({"tipo": "time", "id": 2, "nome": "Vendas"}) == {"tipo": "time", "id": 2, "nome": "Vendas"}
    assert canal.valida_destino_handoff({"tipo": "caixa", "id": 5}) == {"tipo": "caixa", "id": None, "nome": None}
    assert canal.valida_destino_handoff(None) is None
    for invalido in ({"tipo": "usuario"}, {"tipo": "grupo", "id": 1}, {"tipo": "time", "id": -1}):
        with pytest.raises(DestinoInvalido):
            canal.valida_destino_handoff(invalido)


def _evento_de_status(evento: str, status: str, mudou: list[dict[str, Any]]) -> dict[str, Any]:
    return {"event": evento, "id": 1532, "status": status, "inbox_id": 3, "changed_attributes": mudou}


def test_devolucao_para_pendente_vira_retomada_e_atribuicao_nao() -> None:
    from app.canais.base import Acao

    canal = Chatwoot()
    mudou_status = [{"status": {"previous_value": "open", "current_value": "pending"}}]
    atribuiu = [{"assignee_id": {"previous_value": None, "current_value": 7}}]

    for evento in ("conversation_status_changed", "conversation_updated"):
        resultado = canal.interpretar(_evento_de_status(evento, "pending", mudou_status), CREDENCIAIS)
        assert resultado.acao is Acao.RETOMAR and resultado.conversa_externa == "1532"
    assert canal.interpretar(_evento_de_status("conversation_updated", "pending", atribuiu), CREDENCIAIS).acao is Acao.IGNORAR
    abriu = [{"status": {"previous_value": "pending", "current_value": "open"}}]
    assert canal.interpretar(_evento_de_status("conversation_status_changed", "open", abriu), CREDENCIAIS).acao is Acao.IGNORAR
    outra_caixa = {**_evento_de_status("conversation_status_changed", "pending", mudou_status), "inbox_id": 9}
    assert canal.interpretar(outra_caixa, CREDENCIAIS).acao is Acao.IGNORAR


async def test_desconectar_apaga_o_bot_com_o_token_do_administrador() -> None:
    canal = ChatwootHttp(chatwoot_real)
    await canal.desconectar({"token_admin": ADMIN}, CREDENCIAIS)
    assert canal.chamadas == [("DELETE", "/api/v1/accounts/1/agent_bots/99", None)]

    # Bot já apagado no Chatwoot não impede a remoção.
    canal = ChatwootHttp(lambda req, corpo: httpx.Response(404))
    await canal.desconectar({"token_admin": ADMIN}, CREDENCIAIS)

    canal = ChatwootHttp(lambda req, corpo: httpx.Response(401))
    with pytest.raises(CredencialInvalida, match="administrador"):
        await canal.desconectar({"token_admin": "de-atendente"}, CREDENCIAIS)


async def test_devolver_ao_agente_marca_pendente_com_token_do_bot() -> None:
    canal = ChatwootHttp(lambda req, corpo: httpx.Response(200, json={}))
    await canal.devolver_ao_agente(CREDENCIAIS, "12")
    assert canal.chamadas == [("POST", "/api/v1/accounts/1/conversations/12/toggle_status", {"status": "pending"})]


async def test_renomear_troca_o_nome_do_bot_com_token_do_administrador() -> None:
    canal = ChatwootHttp(lambda req, corpo: httpx.Response(200, json={}))
    await canal.renomear({"token_admin": ADMIN}, CREDENCIAIS, "Ticotico")
    assert canal.chamadas == [("PATCH", "/api/v1/accounts/1/agent_bots/99", {"name": "Ticotico"})]

    canal = ChatwootHttp(lambda req, corpo: httpx.Response(401))
    with pytest.raises(CredencialInvalida, match="administrador"):
        await canal.renomear({"token_admin": "x"}, CREDENCIAIS, "Ticotico")
