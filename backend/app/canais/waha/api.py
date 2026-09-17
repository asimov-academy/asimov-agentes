"""Chamadas HTTP à WAHA, que roda na própria VPS (rede interna do Compose, sem porta pública).

A WAHA autentica por `X-Api-Key`, a mesma para toda a instalação: a chave está no `.env` e é lida
aqui, não fica repetida nas credenciais de cada agente. Cada agente tem uma sessão, com o nome
guardado nas credenciais dele.

Endpoints conferidos na documentação da WAHA (2026-09-17):
- `POST /api/sessions` cria e inicia; `GET /api/sessions/{s}` traz `status` e `me`;
  `POST /api/sessions/{s}/start|stop|logout`; `DELETE /api/sessions/{s}` apaga;
- `GET /api/{s}/auth/qr?format=raw` devolve o texto do QR code para desenhar no terminal
  (só com `Accept: application/json`, senão vem a imagem);
- `POST /api/sendText`, `/api/startTyping`, `/api/stopTyping`, `/api/sendSeen` pedem
  `session` e `chatId` no corpo;
- `GET /api/{s}/groups` lista os grupos de que o número participa.
"""

from typing import Any

import httpx

from app.canais.base import CredencialInvalida
from app.plataforma.config import config

TIMEOUT = httpx.Timeout(20.0, connect=5.0)
TIMEOUT_DOWNLOAD = httpx.Timeout(60.0, connect=5.0)

STATUS_PAREADO = "WORKING"
STATUS_QR = "SCAN_QR_CODE"


def cabecalho() -> dict[str, str]:
    return {"X-Api-Key": config().waha_api_key, "Accept": "application/json"}


def raiz() -> str:
    return config().waha_url.rstrip("/")


def _http() -> httpx.AsyncClient:
    return httpx.AsyncClient(timeout=TIMEOUT, headers=cabecalho(), base_url=raiz())


def _erro(acao: str, erro: Exception) -> CredencialInvalida:
    return CredencialInvalida(f"não consegui {acao} na WAHA ({type(erro).__name__})")


def _corpo(resposta: httpx.Response) -> Any:
    try:
        return resposta.json()
    except ValueError:
        return {}


async def _chama(
    metodo: str, caminho: str, acao: str, json: dict[str, Any] | None = None, aceita: tuple[int, ...] = ()
) -> Any:
    try:
        async with _http() as http:
            resposta = await http.request(metodo, caminho, json=json)
    except httpx.HTTPError as erro:
        raise _erro(acao, erro) from erro
    if resposta.status_code in aceita:
        return _corpo(resposta)
    if resposta.status_code == 401:
        raise CredencialInvalida("a WAHA recusou a chave de acesso; rode o setup de novo")
    if resposta.status_code >= 400:
        detalhe = _corpo(resposta)
        mensagem = detalhe.get("message") if isinstance(detalhe, dict) else None
        raise CredencialInvalida(
            f"a WAHA recusou {acao}: HTTP {resposta.status_code}{f' ({mensagem})' if mensagem else ''}"
        )
    return _corpo(resposta)


async def cria_sessao(nome: str, url_webhook: str, chave_hmac: str) -> None:
    """Cria a sessão já com o webhook assinado e a inicia. Sessão que já existe é atualizada."""
    corpo = {
        "name": nome,
        "start": True,
        "config": {
            "webhooks": [
                {
                    "url": url_webhook,
                    "events": ["message", "session.status"],
                    "hmac": {"key": chave_hmac},
                    "retries": {"attempts": 3, "delaySeconds": 2},
                }
            ]
        },
    }
    resposta = await _chama("POST", "/api/sessions", "criar a sessão", corpo, aceita=(409, 422))
    if isinstance(resposta, dict) and resposta.get("name") == nome:
        return
    # Nome já usado (agente removido sem apagar a sessão, ou repetição do setup): reconfigura.
    await _chama("PUT", f"/api/sessions/{nome}", "reconfigurar a sessão", corpo)
    await inicia_sessao(nome)


async def inicia_sessao(nome: str) -> None:
    await _chama("POST", f"/api/sessions/{nome}/start", "iniciar a sessão", aceita=(422,))


async def para_sessao(nome: str) -> None:
    await _chama("POST", f"/api/sessions/{nome}/stop", "parar a sessão", aceita=(404, 422))


async def sai_do_whatsapp(nome: str) -> None:
    """Logout: o aparelho some da lista de aparelhos conectados do WhatsApp."""
    await _chama("POST", f"/api/sessions/{nome}/logout", "desconectar do WhatsApp", aceita=(404, 422))


async def apaga_sessao(nome: str) -> None:
    await _chama("DELETE", f"/api/sessions/{nome}", "apagar a sessão", aceita=(404,))


async def situacao(nome: str) -> dict[str, Any]:
    """`status` da sessão e, quando pareada, o número em `me`. Sessão que sumiu vira STOPPED."""
    resposta = await _chama("GET", f"/api/sessions/{nome}", "ler a sessão", aceita=(404,))
    if not isinstance(resposta, dict) or not resposta.get("status"):
        return {"status": "STOPPED", "me": None}
    return resposta


async def qr_code(nome: str) -> str | None:
    """Texto do QR code. Vazio quando a sessão não está esperando leitura."""
    try:
        async with _http() as http:
            resposta = await http.get(f"/api/{nome}/auth/qr", params={"format": "raw"})
    except httpx.HTTPError as erro:
        raise _erro("ler o QR code", erro) from erro
    if resposta.status_code >= 400:
        return None
    valor = _corpo(resposta)
    return valor.get("value") if isinstance(valor, dict) else None


LIMITE_GRUPOS = 200


async def grupos(nome: str) -> list[dict[str, Any]]:
    """Grupos de que o número participa, para escolher o destino do handoff.

    Sem a lista de participantes (que é grande e não serve aqui) e já em ordem de nome.
    """
    caminho = (
        f"/api/{nome}/groups"
        f"?limit={LIMITE_GRUPOS}&sortBy=subject&sortOrder=asc&exclude=participants"
    )
    resposta = await _chama("GET", caminho, "listar os grupos", aceita=(404, 422, 501))
    itens = resposta if isinstance(resposta, list) else []
    encontrados = []
    for item in itens:
        if not isinstance(item, dict):
            continue
        chat_id = item.get("id")
        if isinstance(chat_id, dict):
            chat_id = chat_id.get("_serialized")
        if not isinstance(chat_id, str) or not chat_id.endswith("@g.us"):
            continue
        titulo = item.get("name") or item.get("subject") or chat_id
        encontrados.append({"chat_id": chat_id, "nome": titulo})
    return encontrados


async def envia_texto(sessao: str, chat_id: str, texto: str) -> str | None:
    resposta = await _chama(
        "POST", "/api/sendText", "enviar a mensagem", {"session": sessao, "chatId": chat_id, "text": texto}
    )
    if not isinstance(resposta, dict):
        return None
    identificador = resposta.get("id")
    if isinstance(identificador, dict):
        identificador = identificador.get("_serialized") or identificador.get("id")
    return str(identificador) if identificador is not None else None


async def digitando(sessao: str, chat_id: str, ligado: bool) -> None:
    caminho = "/api/startTyping" if ligado else "/api/stopTyping"
    await _chama("POST", caminho, "mostrar o digitando", {"session": sessao, "chatId": chat_id})


async def marca_lida(sessao: str, chat_id: str) -> None:
    await _chama("POST", "/api/sendSeen", "marcar como lida", {"session": sessao, "chatId": chat_id})
