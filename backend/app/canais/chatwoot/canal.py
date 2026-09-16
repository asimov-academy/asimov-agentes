"""Canal Chatwoot: Agent Bot com webhook de saída e Application API para responder.

Comportamentos do Chatwoot que quebram integrações e que este arquivo respeita:
- autenticação pelo header `api_access_token`, com token de USUÁRIO (o de bot não muda status);
- a conversa é endereçada pelo display_id, que no payload do webhook vem no campo `id`;
- resposta não 2xx ao webhook faz o Chatwoot silenciar o bot na conversa;
- status `pending` é o agente conduzindo; qualquer outro é humano conduzindo.
"""

from typing import Any

import httpx
from pydantic import BaseModel, Field, HttpUrl, ValidationError

from app.canais.base import Acao, CredencialInvalida, EntradaWebhook, Evento
from app.canais.chatwoot.assinatura import assinatura_confere, timestamp_recente

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
EVENTOS_ACEITOS = frozenset({"message_created", "conversation_updated"})


class CredenciaisChatwoot(BaseModel):
    url: HttpUrl
    account_id: int = Field(gt=0)
    inbox_ids: list[int] = Field(min_length=1)
    api_access_token: str = Field(min_length=1)
    user_id: int | None = None
    bot_secret: str = Field(min_length=1)


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


def _tipo_anexo(payload: dict[str, Any]) -> str:
    anexos = payload.get("attachments") or []
    if not anexos:
        return "texto"
    return {"audio": "audio", "image": "imagem", "video": "video"}.get(
        str(anexos[0].get("file_type")), "documento"
    )


class Chatwoot:
    nome = "chatwoot"
    campos_secretos = frozenset({"api_access_token", "bot_secret"})
    responde_200_em_assinatura_invalida = True

    def _base(self, cred: dict[str, Any]) -> str:
        return f"{str(cred['url']).rstrip('/')}/api/v1/accounts/{cred['account_id']}"

    def _cabecalhos(self, cred: dict[str, Any]) -> dict[str, str]:
        return {"api_access_token": cred["api_access_token"]}

    async def testar(self, credenciais: dict[str, Any]) -> dict[str, Any]:
        try:
            cred = CredenciaisChatwoot.model_validate(credenciais)
        except ValidationError as erro:
            campos = ", ".join(str(e["loc"][0]) for e in erro.errors())
            raise CredencialInvalida(f"credenciais do Chatwoot incompletas: {campos}") from erro

        dados = cred.model_dump(mode="json")
        base_url = str(cred.url).rstrip("/")
        try:
            async with httpx.AsyncClient(timeout=TIMEOUT) as http:
                perfil = await http.get(
                    f"{base_url}/api/v1/profile", headers=self._cabecalhos(dados)
                )
                if perfil.status_code == 401:
                    raise CredencialInvalida("api_access_token recusado pelo Chatwoot")
                perfil.raise_for_status()
                inboxes = await http.get(
                    f"{self._base(dados)}/inboxes", headers=self._cabecalhos(dados)
                )
        except httpx.HTTPError as erro:
            raise CredencialInvalida(f"não consegui falar com o Chatwoot em {base_url}") from erro

        if inboxes.status_code in (401, 403, 404):
            raise CredencialInvalida(
                f"o usuário do token não acessa a conta {cred.account_id} do Chatwoot"
            )
        corpo = inboxes.json()
        lista = corpo.get("payload", []) if isinstance(corpo, dict) else corpo
        existentes = {i.get("id") for i in lista if isinstance(i, dict)}
        faltando = [i for i in cred.inbox_ids if i not in existentes]
        if faltando:
            raise CredencialInvalida(f"inbox não encontrada na conta: {faltando}")

        if dados.get("user_id") is None:
            dados["user_id"] = perfil.json().get("id")
        return dados

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
            "tipo": _tipo_anexo(payload),
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
            if not (payload.get("content") or "").strip():
                return Evento(Acao.REGISTRAR, "anexo sem texto", **base, **contato)
            return Evento(Acao.PROCESSAR, "mensagem do contato", **base, **contato)

        if tipo_mensagem in ("outgoing", 1):
            if remetente.get("id") == credenciais.get("user_id") and remetente.get("type") in (
                "user",
                None,
            ):
                return Evento(Acao.IGNORAR, "mensagem enviada pelo próprio agente", conversa)
            return Evento(
                Acao.REGISTRAR, "mensagem de atendente", **base, autor="humano", direcao="saida"
            )

        return Evento(Acao.IGNORAR, f"message_type {tipo_mensagem!r}", conversa)

    async def agente_pode_falar(self, credenciais: dict[str, Any], conversa_externa: str) -> bool:
        async with httpx.AsyncClient(timeout=TIMEOUT) as http:
            resp = await http.get(
                f"{self._base(credenciais)}/conversations/{conversa_externa}",
                headers=self._cabecalhos(credenciais),
            )
        resp.raise_for_status()
        return resp.json().get("status") == "pending"

    async def digitando(
        self, credenciais: dict[str, Any], conversa_externa: str, ligado: bool
    ) -> None:
        async with httpx.AsyncClient(timeout=TIMEOUT) as http:
            await http.post(
                f"{self._base(credenciais)}/conversations/{conversa_externa}/toggle_typing_status",
                json={"typing_status": "on" if ligado else "off"},
                headers=self._cabecalhos(credenciais),
            )

    async def enviar_texto(
        self, credenciais: dict[str, Any], conversa_externa: str, texto: str
    ) -> str | None:
        async with httpx.AsyncClient(timeout=TIMEOUT) as http:
            resp = await http.post(
                f"{self._base(credenciais)}/conversations/{conversa_externa}/messages",
                json={"content": texto, "message_type": "outgoing", "private": False},
                headers=self._cabecalhos(credenciais),
            )
        resp.raise_for_status()
        mensagem_id = resp.json().get("id")
        return str(mensagem_id) if mensagem_id is not None else None
