"""Canal Chatwoot: Agent Bot com webhook de saída e Application API para responder.

Conexão: o operador informa a URL do Chatwoot e o token de um ADMINISTRADOR. Com ele o canal
cria o Agent Bot já apontando para o webhook do agente e liga o bot nas caixas de entrada.
O token do administrador fica em `acessos/` (cifrado) para criar, renomear e apagar bots; na
conversa só se usa o token do próprio bot.

Comportamentos do Chatwoot que este arquivo respeita (conferidos no código do Chatwoot):
- autenticação pelo header `api_access_token`;
- o token de bot alcança ver conversa, mudar status, digitando, atribuição e criar mensagem
  (`BOT_ACCESSIBLE_ENDPOINTS` em `access_token_auth_helper.rb`);
- criar bot e ligar bot em caixa de entrada exige administrador;
- a conversa é endereçada pelo display_id, que no payload do webhook vem no campo `id`;
- resposta não 2xx ao webhook faz o Chatwoot silenciar o bot na conversa;
- status `pending` é o agente conduzindo; qualquer outro é humano conduzindo;
- `toggle_status` de `pending` para `open` feito pelo bot é o handoff do Chatwoot (`bot_handoff!`);
- mudança de status chega ao bot como `conversation_status_changed` e `conversation_updated`,
  com `changed_attributes`; atribuição sozinha chega só como `conversation_updated`.
"""

import mimetypes
from typing import Any, Literal
from urllib.parse import urlsplit

import httpx
import structlog
from pydantic import BaseModel, Field, HttpUrl, ValidationError, model_validator

from app.canais.base import (
    Acao,
    AcessoRecusado,
    Anexo,
    ArquivoBaixado,
    ArquivoGrandeDemais,
    CredencialInvalida,
    DestinoInvalido,
    EntradaWebhook,
    Evento,
)
from app.canais.chatwoot.assinatura import assinatura_confere, timestamp_recente

log = structlog.get_logger()

TIMEOUT = httpx.Timeout(10.0, connect=5.0)
TIMEOUT_DOWNLOAD = httpx.Timeout(60.0, connect=5.0)
EVENTOS_DE_STATUS = frozenset({"conversation_status_changed", "conversation_updated"})
EVENTOS_ACEITOS = frozenset({"message_created"}) | EVENTOS_DE_STATUS


class AcessoChatwoot(BaseModel):
    url: HttpUrl
    token_admin: str = Field(min_length=1)


class AcessoAdmin(BaseModel):
    """Para desfazer a conexão: URL e conta já estão nas credenciais do agente."""

    token_admin: str = Field(min_length=1)


class ConexaoChatwoot(AcessoChatwoot):
    account_id: int = Field(gt=0)
    inbox_ids: list[int] = Field(min_length=1)


class DestinoHandoff(BaseModel):
    """Quem recebe a conversa: um usuário, um time ou a caixa sem atribuição."""

    tipo: Literal["usuario", "time", "caixa"]
    id: int | None = Field(default=None, gt=0)
    nome: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _id_quando_precisa(self) -> "DestinoHandoff":
        if self.tipo != "caixa" and self.id is None:
            raise ValueError(f"destino {self.tipo} precisa do id")
        if self.tipo == "caixa":
            self.id = None
        return self


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


def _status_mudou(payload: dict[str, Any]) -> bool:
    """`changed_attributes` vem como lista de `{campo: {previous_value, current_value}}`."""
    mudancas = payload.get("changed_attributes")
    if isinstance(mudancas, dict):
        mudancas = [mudancas]
    return any(isinstance(m, dict) and "status" in m for m in mudancas or [])


class Chatwoot:
    nome = "chatwoot"
    campos_secretos = frozenset({"api_access_token", "bot_secret"})
    responde_200_em_assinatura_invalida = True
    retoma_por_tempo = True
    pede_acesso_do_operador = True
    externo = True
    webhook_interno = False
    """A conversa volta ao agente quando o atendente a devolve para pendente, ou sozinha depois de
    `retomada_automatica_horas` se ninguém devolver."""

    def _http(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(timeout=TIMEOUT)

    def _base(self, url: Any, account_id: int) -> str:
        return f"{_raiz(url)}/api/v1/accounts/{account_id}"

    # ── Conexão (setup e menu) ─────────────────────────────────────────────

    def acesso_do_operador(self, dados: dict[str, Any]) -> dict[str, Any]:
        token = dados.get("token_admin")
        return {"token_admin": token} if isinstance(token, str) and token.strip() else {}

    def endereco(self, dados: dict[str, Any]) -> str:
        url = dados.get("url")
        if not isinstance(url, str) or not url.startswith(("https://", "http://")):
            raise CredencialInvalida("dados do Chatwoot incompletos: url")
        return _raiz(url)

    async def descobrir(self, dados: dict[str, Any]) -> dict[str, Any]:
        """Contas e caixas de entrada que o token do administrador enxerga."""
        acesso: AcessoChatwoot = _valida(AcessoChatwoot, dados)
        cabecalho = {"api_access_token": acesso.token_admin}
        try:
            async with self._http() as http:
                perfil = await http.get(f"{_raiz(acesso.url)}/api/v1/profile", headers=cabecalho)
                if perfil.status_code == 401:
                    raise AcessoRecusado("token recusado pelo Chatwoot")
                perfil.raise_for_status()
                contas = []
                for conta in perfil.json().get("accounts", []):
                    base = self._base(acesso.url, conta["id"])
                    resp = await http.get(f"{base}/inboxes", headers=cabecalho)
                    caixas = _lista(resp.json()) if resp.status_code == 200 else []
                    # Destinos de handoff. Time pode estar desligado na conta: vira lista vazia.
                    resp = await http.get(f"{base}/agents", headers=cabecalho)
                    atendentes = _lista(resp.json()) if resp.status_code == 200 else []
                    resp = await http.get(f"{base}/teams", headers=cabecalho)
                    times = _lista(resp.json()) if resp.status_code == 200 else []
                    contas.append(
                        {
                            "id": conta["id"],
                            "nome": conta.get("name"),
                            "caixas": [
                                {"id": c["id"], "nome": c.get("name"), "tipo": c.get("channel_type")}
                                for c in caixas
                            ],
                            "atendentes": [{"id": a["id"], "nome": a.get("name")} for a in atendentes],
                            "times": [{"id": i["id"], "nome": i.get("name")} for i in times],
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
                    raise AcessoRecusado(
                        "o token precisa ser de um administrador da conta do Chatwoot"
                    )
                resp.raise_for_status()
                bot = resp.json()
                if not bot.get("access_token") or not bot.get("secret"):
                    await http.delete(f"{base}/agent_bots/{bot['id']}", headers=cabecalho)
                    raise AcessoRecusado(
                        "o Chatwoot não devolveu o token do bot; confira se o usuário é administrador"
                    )
                for inbox_id in conexao.inbox_ids:
                    ligado = await http.post(
                        f"{base}/inboxes/{inbox_id}/set_agent_bot",
                        json={"agent_bot": bot["id"]},
                        headers=cabecalho,
                    )
                    if ligado.status_code >= 400 or not await self._bot_ligado(
                        http, base, cabecalho, inbox_id, bot["id"]
                    ):
                        await http.delete(f"{base}/agent_bots/{bot['id']}", headers=cabecalho)
                        raise CredencialInvalida(
                            f"o Chatwoot não ligou o bot na caixa de entrada {inbox_id}; "
                            "confira se ela aceita bot e tente de novo"
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

    async def _bot_ligado(
        self, http: httpx.AsyncClient, base: str, cabecalho: dict[str, str], inbox_id: int, bot_id: int
    ) -> bool:
        """Confere na caixa qual bot ficou. O Chatwoot responde 200 mesmo quando não liga.

        Chatwoot sem a rota de consulta (versão antiga) não impede: vale a resposta da ligação.
        """
        resp = await http.get(f"{base}/inboxes/{inbox_id}/agent_bot", headers=cabecalho)
        if resp.status_code == 404:
            return True
        if resp.status_code >= 400:
            return False
        try:
            ligado = (resp.json() or {}).get("agent_bot") or {}
        except ValueError:
            return True
        return ligado.get("id") == bot_id

    async def desconectar(self, dados: dict[str, Any], credenciais: dict[str, Any]) -> None:
        """Apaga o Agent Bot; o Chatwoot desliga o bot das caixas junto. Bot que já não existe é ok."""
        acesso: AcessoAdmin = _valida(AcessoAdmin, dados)
        try:
            async with self._http() as http:
                resp = await http.delete(
                    f"{self._base_operacao(credenciais)}/agent_bots/{credenciais['bot_id']}",
                    headers={"api_access_token": acesso.token_admin},
                )
        except httpx.HTTPError as erro:
            raise CredencialInvalida(
                f"não consegui falar com o Chatwoot em {credenciais['url']}"
            ) from erro
        if resp.status_code in (401, 403):
            raise AcessoRecusado("o token precisa ser de um administrador da conta do Chatwoot")
        if resp.status_code >= 400 and resp.status_code != 404:
            raise CredencialInvalida(f"o Chatwoot recusou apagar o bot: HTTP {resp.status_code}")

    async def renomear(self, dados: dict[str, Any], credenciais: dict[str, Any], nome: str) -> None:
        """Nome do Agent Bot, que aparece nas mensagens do agente. Editar bot exige administrador."""
        acesso: AcessoAdmin = _valida(AcessoAdmin, dados)
        try:
            async with self._http() as http:
                resp = await http.patch(
                    f"{self._base_operacao(credenciais)}/agent_bots/{credenciais['bot_id']}",
                    json={"name": nome},
                    headers={"api_access_token": acesso.token_admin},
                )
        except httpx.HTTPError as erro:
            raise CredencialInvalida(
                f"não consegui falar com o Chatwoot em {credenciais['url']}"
            ) from erro
        if resp.status_code in (401, 403):
            raise AcessoRecusado("o token precisa ser de um administrador da conta do Chatwoot")
        if resp.status_code >= 400:
            raise CredencialInvalida(f"o Chatwoot recusou renomear o bot: HTTP {resp.status_code}")

    # ── Operação (token do bot) ────────────────────────────────────────────

    def responde_verificacao(self, parametros: dict[str, str], token: str) -> str | None:
        """Este canal não confere o endereço do webhook por GET."""
        return None

    def verificar(self, entrada: EntradaWebhook, credenciais: dict[str, Any]) -> bool:
        ts = entrada.cabecalhos.get("x-chatwoot-timestamp", "")
        assinatura = entrada.cabecalhos.get("x-chatwoot-signature", "")
        return timestamp_recente(ts) and assinatura_confere(
            credenciais.get("bot_secret", ""), ts, assinatura, entrada.corpo
        )

    def interpretar(
        self, payload: dict[str, Any], credenciais: dict[str, Any], destino: dict[str, Any] | None = None
    ) -> Evento:
        evento = payload.get("event")
        if evento not in EVENTOS_ACEITOS:
            return Evento(Acao.IGNORAR, f"evento fora da lista: {evento!r}")

        # Sem filtro por caixa: o Chatwoot só chama o bot a partir das caixas em que ele está ligado,
        # e a assinatura prova qual bot é. Ligar o bot em outra caixa pelo Chatwoot também vale.
        conversa = _id_conversa(payload)
        if conversa is None:
            return Evento(Acao.IGNORAR, "payload sem id de conversa")

        if evento in EVENTOS_DE_STATUS:
            # Só mudança de status para pendente devolve. A atribuição feita no handoff chega
            # como conversation_updated ainda com status pendente e não pode fechar o handoff.
            if _conversa(payload).get("status") == "pending" and _status_mudou(payload):
                return Evento(Acao.RETOMAR, "conversa devolvida ao agente", conversa)
            return Evento(Acao.IGNORAR, f"{evento} sem devolução", conversa)

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
                return Evento(
                    Acao.IGNORAR,
                    f"mensagem de entrada sem remetente (sender do tipo {remetente.get('type')!r}, campos {sorted(remetente)})",
                    conversa,
                )
            if _conversa(payload).get("status") != "pending":
                return Evento(Acao.REGISTRAR, "humano conduz a conversa", **base, **contato)
            if not (payload.get("content") or "").strip() and not base["anexos"]:
                return Evento(Acao.REGISTRAR, "mensagem sem conteúdo", **base, **contato)
            return Evento(Acao.PROCESSAR, "mensagem do contato", **base, **contato)

        if tipo_mensagem in ("outgoing", 1):
            if remetente.get("type") == "agent_bot":
                return Evento(Acao.IGNORAR, "mensagem enviada por bot", conversa)
            # Atendente respondeu: a conversa passa a ser dele, e o agente só volta quando ela for
            # devolvida para pendente ou o prazo do agente vencer.
            return Evento(
                Acao.PAUSAR,
                "mensagem de atendente",
                **base,
                autor="humano",
                direcao="saida",
                autor_externo=str(remetente["id"]) if remetente.get("id") is not None else None,
            )

        return Evento(Acao.IGNORAR, f"message_type {tipo_mensagem!r}", conversa)

    def valida_destino_handoff(self, destino: dict[str, Any] | None) -> dict[str, Any] | None:
        if destino is None:
            return None
        try:
            return DestinoHandoff.model_validate(destino).model_dump()
        except ValidationError as erro:
            raise DestinoInvalido(
                "destino de handoff do Chatwoot deve ser usuário ou time com id, ou caixa"
            ) from erro

    async def transferir(
        self,
        credenciais: dict[str, Any],
        conversa_externa: str,
        destino: dict[str, Any] | None,
        nota: str,
        codigo: str = "",
        contato: str = "",
    ) -> list[str]:
        """Nota privada, atribuição e status aberto, nessa ordem.

        Atribuir antes de abrir evita que a distribuição automática da caixa escolha outra pessoa.
        Sem destino (ou destino `caixa`) a conversa fica aberta na caixa, sem atribuição.
        """
        base = f"{self._base_operacao(credenciais)}/conversations/{conversa_externa}"
        cabecalho = self._cabecalho_bot(credenciais)
        problemas: list[str] = []
        async with self._http() as http:
            try:
                resp = await http.post(
                    f"{base}/messages",
                    json={"content": nota, "message_type": "outgoing", "private": True},
                    headers=cabecalho,
                )
                if resp.status_code >= 400:
                    problemas.append(f"nota recusada: HTTP {resp.status_code}")
            except httpx.HTTPError as erro:
                problemas.append(f"nota falhou: {type(erro).__name__}")

            alvo = destino or {}
            if alvo.get("tipo") in ("usuario", "time"):
                chave = "assignee_id" if alvo["tipo"] == "usuario" else "team_id"
                corpo = {chave: alvo["id"]}
                try:
                    resp = await http.post(f"{base}/assignments", json=corpo, headers=cabecalho)
                    if resp.status_code >= 400:
                        problemas.append(f"atribuição recusada: HTTP {resp.status_code}")
                except httpx.HTTPError as erro:
                    problemas.append(f"atribuição falhou: {type(erro).__name__}")

            resp = await http.post(
                f"{base}/toggle_status", json={"status": "open"}, headers=cabecalho
            )
            resp.raise_for_status()
        return problemas

    def _base_operacao(self, credenciais: dict[str, Any]) -> str:
        return self._base(credenciais["url"], credenciais["account_id"])

    def _cabecalho_bot(self, credenciais: dict[str, Any]) -> dict[str, str]:
        return {"api_access_token": credenciais["api_access_token"]}

    async def agente_pode_falar(
        self, credenciais: dict[str, Any], conversa_externa: str, status: str
    ) -> bool:
        """Quem manda é o Chatwoot: o atendente pode ter assumido a conversa por lá."""
        async with self._http() as http:
            resp = await http.get(
                f"{self._base_operacao(credenciais)}/conversations/{conversa_externa}",
                headers=self._cabecalho_bot(credenciais),
            )
        resp.raise_for_status()
        return resp.json().get("status") == "pending"

    def rotulo_da_conversa(self, conversa_externa: str) -> str:
        return f"a conversa {conversa_externa}"

    async def avisa_destino(
        self, credenciais: dict[str, Any], destino: dict[str, Any] | None, texto: str
    ) -> None:
        """No Chatwoot o atendente vê a conversa voltar para pendente: nada a avisar."""
        return None

    async def devolver_ao_agente(self, credenciais: dict[str, Any], conversa_externa: str) -> None:
        """Pendente é o agente conduzindo. O Chatwoot avisa a mudança pelo webhook, que é idempotente.

        Tira também a atribuição do atendente: conversa pendente com dono confunde quem olha a fila,
        e quem está conduzindo dali em diante é o bot. Recusa na atribuição não impede a devolução.
        """
        base = f"{self._base_operacao(credenciais)}/conversations/{conversa_externa}"
        cabecalho = self._cabecalho_bot(credenciais)
        async with self._http() as http:
            resp = await http.post(f"{base}/toggle_status", json={"status": "pending"}, headers=cabecalho)
            resp.raise_for_status()
            try:
                await http.post(f"{base}/assignments", json={"assignee_id": 0}, headers=cabecalho)
            except httpx.HTTPError as erro:
                log.warning("desatribuir_falhou", erro=repr(erro))

    async def assumir_no_canal(
        self, credenciais: dict[str, Any], conversa_externa: str, autor_externo: str | None
    ) -> None:
        """Atendente respondeu: conversa aberta e atribuída a ele, para sair da fila do bot.

        O Chatwoot pode já ter feito os dois, conforme a configuração da caixa; repetir não muda nada.
        """
        base = f"{self._base_operacao(credenciais)}/conversations/{conversa_externa}"
        cabecalho = self._cabecalho_bot(credenciais)
        async with self._http() as http:
            resp = await http.post(f"{base}/toggle_status", json={"status": "open"}, headers=cabecalho)
            resp.raise_for_status()
            if autor_externo and autor_externo.isdigit():
                atribuiu = await http.post(
                    f"{base}/assignments", json={"assignee_id": int(autor_externo)}, headers=cabecalho
                )
                if atribuiu.status_code >= 400:
                    log.warning("atribuir_ao_atendente_recusado", status=atribuiu.status_code)

    async def digitando(
        self,
        credenciais: dict[str, Any],
        conversa_externa: str,
        ligado: bool,
        ultima_mensagem: str | None = None,
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
