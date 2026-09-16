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
    assert resultado == {"contas": [{"id": 1, "nome": "Loja Exemplo", "caixas": [{"id": 3, "nome": "WhatsApp", "tipo": "Channel::Whatsapp"}]}]}


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
