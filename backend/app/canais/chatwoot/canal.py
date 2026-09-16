"""Canal Chatwoot: Agent Bot com webhook de saída e Application API para responder.

Conexão: o operador informa a URL do Chatwoot e o token de um ADMINISTRADOR. Com ele o canal
cria o Agent Bot já apontando para o webhook do agente e liga o bot nas caixas de entrada.
O token do administrador não é guardado: em operação só se usa o token do próprio bot.

Comportamentos do Chatwoot que este arquivo respeita (conferidos no código do Chatwoot):
- autenticação pelo header `api_access_token`;
- o token de bot alcança ver conversa, mudar status, digitando, atribuição e criar mensagem
  (`BOT_ACCESSIBLE_ENDPOINTS` em `access_token_auth_helper.rb`);
- criar bot e ligar bot em caixa de entrada exige administrador;
- a conversa é endereçada pelo display_id, que no payload do webhook vem no campo `id`;
- resposta não 2xx ao webhook faz o Chatwoot silenciar o bot na conversa;
- status `pending` é o agente conduzindo; qualquer outro é humano conduzindo.
"""

import mimetypes
from typing import Any
from urllib.parse import urlsplit

import httpx
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from app.canais.base import (
    Acao,
    Anexo,
    ArquivoBaixado,
    ArquivoGrandeDemais,
    CredencialInvalida,
    EntradaWebhook,
    Evento,
)
from app.canais.chatwoot.assinatura import assinatura_confere, timestamp_recente

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
TIMEOUT_DOWNLOAD = httpx.Timeout(60.0, connect=5.0)
EVENTOS_ACEITOS = frozenset({"message_created", "conversation_updated"})


class AcessoChatwoot(BaseModel):
    url: HttpUrl
    token_admin: str = Field(min_length=1)


class ConexaoChatwoot(AcessoChatwoot):
    account_id: int = Field(gt=0)
    inbox_ids: list[int] = Field(min_length=1)


class CredenciaisChatwoot(BaseModel):
    """O que fica guardado (cifrado). Nada do administrador."""

    url: str
    account_id: int
    inbox_ids: list[int]
    api_access_token: str
    bot_id: int
    bot_secret: str


def _valida(modelo: type[BaseModel], dados: dict[str, Any]) -> Any:
    try:
        return modelo.model_validate(dados)
    except ValidationError as erro:
        campos = ", ".join(str(e["loc"][0]) for e in erro.errors())
        raise CredencialInvalida(f"dados do Chatwoot incompletos: {campos}") from erro


def _raiz(url: Any) -> str:
    return str(url).rstrip("/")


def _conversa(payload: dict[str, Any]) -> dict[str, Any]:
    aninhada = payload.get("conversation")
    return aninhada if isinstance(aninhada, dict) else payload


def _id_conversa(payload: dict[str, Any]) -> str | None:
    conversa = _conversa(payload)
    for chave in ("display_id", "id"):
        valor = conversa.get(chave)
        if isinstance(valor, int):
            return str(valor)
    return None


def _id_inbox(payload: dict[str, Any]) -> int | None:
    conversa = _conversa(payload)
    for fonte in (payload.get("inbox"), conversa.get("inbox")):
        if isinstance(fonte, dict) and isinstance(fonte.get("id"), int):
            return fonte["id"]
    for fonte in (payload, conversa):
        if isinstance(fonte.get("inbox_id"), int):
            return fonte["inbox_id"]
    return None


TIPOS_ANEXO = {"audio": "audio", "image": "imagem", "video": "video", "file": "documento"}
"""Localização, contato e cartões do Instagram não têm arquivo para baixar."""


def _anexos(payload: dict[str, Any]) -> tuple[Anexo, ...]:
    anexos = []
    for item in payload.get("attachments") or []:
        if not isinstance(item, dict):
            continue
        tipo = TIPOS_ANEXO.get(str(item.get("file_type")))
        url = item.get("data_url")
        if tipo is None or not isinstance(url, str) or not url.startswith(("https://", "http://")):
            continue
        tamanho = item.get("file_size")
        anexos.append(
            Anexo(
                tipo=tipo,
                referencia=url,
                tamanho_bytes=tamanho if isinstance(tamanho, int) else None,
                nome=urlsplit(url).path.rsplit("/", 1)[-1] or None,
            )
        )
    return tuple(anexos)


def _lista(corpo: Any) -> list[dict[str, Any]]:
    itens = corpo.get("payload", []) if isinstance(corpo, dict) else corpo
    return [i for i in itens or [] if isinstance(i, dict)]


class Chatwoot:
    nome = "chatwoot"
    campos_secretos = frozenset({"api_access_token", "bot_secret"})
    responde_200_em_assinatura_invalida = True

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=TIMEOUT)

    def _base(self, url: Any, account_id: int) -> str:
        return f"{_raiz(url)}/api/v1/accounts/{account_id}"

    # ── Conexão (setup e menu) ─────────────────────────────────────────────

    async def descobrir(self, dados: dict[str, Any]) -> dict[str, Any]:
        """Contas e caixas de entrada que o token do administrador enxerga."""
        acesso: AcessoChatwoot = _valida(AcessoChatwoot, dados)
        cabecalho = {"api_access_token": acesso.token_admin}
        try:
            async with self._http() as http:
                perfil = await http.get(f"{_raiz(acesso.url)}/api/v1/profile", headers=cabecalho)
                if perfil.status_code == 401:
                    raise CredencialInvalida("token recusado pelo Chatwoot")
                perfil.raise_for_status()
                contas = []
                for conta in perfil.json().get("accounts", []):
                    resp = await http.get(
                        f"{self._base(acesso.url, conta['id'])}/inboxes", headers=cabecalho
                    )
                    caixas = _lista(resp.json()) if resp.status_code == 200 else []
                    contas.append(
                        {
                            "id": conta["id"],
                            "nome": conta.get("name"),
                            "caixas": [
                                {"id": c["id"], "nome": c.get("name"), "tipo": c.get("channel_type")}
                                for c in caixas
                            ],
                        }
                    )
        except CredencialInvalida:
            raise
        except httpx.HTTPError as erro:
            raise CredencialInvalida(f"não consegui falar com o Chatwoot em {_raiz(acesso.url)}") from erro
        except (ValueError, KeyError) as erro:
            raise CredencialInvalida(f"{_raiz(acesso.url)} não respondeu como um Chatwoot") from erro
        if not contas:
            raise CredencialInvalida("esse usuário não tem nenhuma conta no Chatwoot")
        return {"contas": contas}

    async def conectar(
        self, dados: dict[str, Any], url_webhook: str, nome_agente: str
    ) -> dict[str, Any]:
        """Cria o Agent Bot apontando para o webhook e liga o bot nas caixas de entrada."""
        conexao: ConexaoChatwoot = _valida(ConexaoChatwoot, dados)
        base = self._base(conexao.url, conexao.account_id)
        cabecalho = {"api_access_token": conexao.token_admin}
        try:
            async with self._http() as http:
                resp = await http.post(
                    f"{base}/agent_bots",
                    json={
                        "name": nome_agente,
                        "description": "Criado pelo setup Asimov Academy",
                        "outgoing_url": url_webhook,
                    },
                    headers=cabecalho,
                )
                if resp.status_code in (401, 403):
                    raise CredencialInvalida(
                        "o token precisa ser de um administrador da conta do Chatwoot"
                    )
                resp.raise_for_status()
                bot = resp.json()
                if not bot.get("access_token") or not bot.get("secret"):
                    await http.delete(f"{base}/agent_bots/{bot['id']}", headers=cabecalho)
                    raise CredencialInvalida(
                        "o Chatwoot não devolveu o token do bot; confira se o usuário é administrador"
                    )
                for inbox_id in conexao.inbox_ids:
                    ligado = await http.post(
                        f"{base}/inboxes/{inbox_id}/set_agent_bot",
                        json={"agent_bot": bot["id"]},
                        headers=cabecalho,
                    )
                    if ligado.status_code >= 400:
                        await http.delete(f"{base}/agent_bots/{bot['id']}", headers=cabecalho)
                        raise CredencialInvalida(
                            f"não consegui ligar o bot na caixa de entrada {inbox_id}"
                        )
        except httpx.HTTPError as erro:
            raise CredencialInvalida(
                f"não consegui falar com o Chatwoot em {_raiz(conexao.url)}"
            ) from erro

        return CredenciaisChatwoot(
            url=_raiz(conexao.url),
            account_id=conexao.account_id,
            inbox_ids=conexao.inbox_ids,
            api_access_token=bot["access_token"],
            bot_id=bot["id"],
            bot_secret=bot["secret"],
        ).model_dump()

    async def desconectar(self, dados: dict[str, Any], credenciais: dict[str, Any]) -> None:
        """Desfaz `conectar` quando o agente não chega a ser gravado."""
        conexao: ConexaoChatwoot = _valida(ConexaoChatwoot, dados)
        async with self._http() as http:
            await http.delete(
                f"{self._base(conexao.url, conexao.account_id)}/agent_bots/{credenciais['bot_id']}",
                headers={"api_access_token": conexao.token_admin},
            )

    # ── Operação (token do bot) ────────────────────────────────────────────

    def verificar(self, entrada: EntradaWebhook, credenciais: dict[str, Any]) -> bool:
        ts = entrada.cabecalhos.get("x-chatwoot-timestamp", "")
        assinatura = entrada.cabecalhos.get("x-chatwoot-signature", "")
        return timestamp_recente(ts) and assinatura_confere(
            credenciais.get("bot_secret", ""), ts, assinatura, entrada.corpo
        )

    def interpretar(self, payload: dict[str, Any], credenciais: dict[str, Any]) -> Evento:
        evento = payload.get("event")
        if evento not in EVENTOS_ACEITOS:
            return Evento(Acao.IGNORAR, f"evento fora da lista: {evento!r}")

        inbox = _id_inbox(payload)
        if inbox is not None and inbox not in credenciais.get("inbox_ids", []):
            return Evento(Acao.IGNORAR, f"inbox {inbox} não é deste agente")

        conversa = _id_conversa(payload)
        if conversa is None:
            return Evento(Acao.IGNORAR, "payload sem id de conversa")

        if evento == "conversation_updated":
            # Retomada e transferência chegam por aqui na fase 3.
            return Evento(Acao.IGNORAR, "conversation_updated ainda sem uso", conversa)

        if payload.get("private") is True:
            return Evento(Acao.IGNORAR, "nota privada", conversa)

        remetente = payload.get("sender") or {}
        tipo_mensagem = payload.get("message_type")
        base = {
            "conversa_externa": conversa,
            "mensagem_externa": str(payload["id"]) if payload.get("id") is not None else None,
            "texto": payload.get("content"),
            "anexos": _anexos(payload),
        }

        if tipo_mensagem in ("incoming", 0):
            contato = {
                "contato_externo": str(remetente.get("id")) if remetente.get("id") else None,
                "contato_nome": remetente.get("name"),
                "contato_telefone": remetente.get("phone_number"),
            }
            if contato["contato_externo"] is None:
                return Evento(Acao.IGNORAR, "mensagem de entrada sem remetente", conversa)
            if _conversa(payload).get("status") != "pending":
                return Evento(Acao.REGISTRAR, "humano conduz a conversa", **base, **contato)
            if not (payload.get("content") or "").strip() and not base["anexos"]:
                return Evento(Acao.REGISTRAR, "mensagem sem conteúdo", **base, **contato)
            return Evento(Acao.PROCESSAR, "mensagem do contato", **base, **contato)

        if tipo_mensagem in ("outgoing", 1):
            if remetente.get("type") == "agent_bot":
                return Evento(Acao.IGNORAR, "mensagem enviada por bot", conversa)
            return Evento(
                Acao.REGISTRAR, "mensagem de atendente", **base, autor="humano", direcao="saida"
            )

        return Evento(Acao.IGNORAR, f"message_type {tipo_mensagem!r}", conversa)

    def _base_operacao(self, credenciais: dict[str, Any]) -> str:
        return self._base(credenciais["url"], credenciais["account_id"])

    def _cabecalho_bot(self, credenciais: dict[str, Any]) -> dict[str, str]:
        return {"api_access_token": credenciais["api_access_token"]}

    async def agente_pode_falar(self, credenciais: dict[str, Any], conversa_externa: str) -> bool:
        async with self._http() as http:
            resp = await http.get(
                f"{self._base_operacao(credenciais)}/conversations/{conversa_externa}",
                headers=self._cabecalho_bot(credenciais),
            )
        resp.raise_for_status()
        return resp.json().get("status") == "pending"

    async def digitando(
        self, credenciais: dict[str, Any], conversa_externa: str, ligado: bool
    ) -> None:
        async with self._http() as http:
            await http.post(
                f"{self._base_operacao(credenciais)}/conversations/{conversa_externa}/toggle_typing_status",
                json={"typing_status": "on" if ligado else "off"},
                headers=self._cabecalho_bot(credenciais),
            )

    async def enviar_texto(
        self, credenciais: dict[str, Any], conversa_externa: str, texto: str
    ) -> str | None:
        async with self._http() as http:
            resp = await http.post(
                f"{self._base_operacao(credenciais)}/conversations/{conversa_externa}/messages",
                json={"content": texto, "message_type": "outgoing", "private": False},
                headers=self._cabecalho_bot(credenciais),
            )
        resp.raise_for_status()
        mensagem_id = resp.json().get("id")
        return str(mensagem_id) if mensagem_id is not None else None

    async def baixar_midia(
        self, credenciais: dict[str, Any], anexo: Anexo, limite_bytes: int
    ) -> ArquivoBaixado:
        """`data_url` é um link assinado do Chatwoot que redireciona para o armazenamento.

        Vai sem o token do bot: o link já autoriza, e o httpx repassaria o header no redirect.
        """
        if anexo.tamanho_bytes is not None and anexo.tamanho_bytes > limite_bytes:
            raise ArquivoGrandeDemais(f"{anexo.tamanho_bytes} bytes")
        partes: list[bytes] = []
        total = 0
        async with httpx.AsyncClient(timeout=TIMEOUT_DOWNLOAD, follow_redirects=True) as http:
            async with http.stream("GET", anexo.referencia) as resp:
                resp.raise_for_status()
                async for parte in resp.aiter_bytes():
                    total += len(parte)
                    if total > limite_bytes:
                        raise ArquivoGrandeDemais(f"mais de {limite_bytes} bytes")
                    partes.append(parte)
                mime = resp.headers.get("content-type", "").split(";")[0].strip().lower()
        if not mime or mime == "application/octet-stream":
            mime = mimetypes.guess_type(anexo.nome or "")[0] or anexo.tipo_mime or mime
        return ArquivoBaixado(conteudo=b"".join(partes), tipo_mime=mime or "application/octet-stream")
