"""Canal WAHA: WhatsApp direto, por um número pareado por QR code na própria VPS.

Uma sessão da WAHA por agente, criada na conexão já apontando para o webhook interno
(`http://api:8000/webhook/waha/{token}`), com assinatura HMAC sorteada por agente. Não há acesso
de operador: a WAHA é da instalação, e a chave dela está no `.env`.

Diferenças para o Chatwoot, que este arquivo respeita:
- não existe "conversa aberta com atendente": quem guarda a pausa do handoff é o status da
  conversa aqui (`agente_pode_falar` responde por ele);
- o handoff avisa um número ou grupo escolhido pelo operador, com resumo e código, e volta com
  `/retomar <código>` mandado por esse destino ou sozinho, pelo tempo do agente;
- mensagem de grupo só é lida quando vem do grupo do handoff; `fromMe` nunca é lida (é o próprio
  número respondendo, inclusive as mensagens que o agente acabou de enviar).
"""

import re
import secrets
import uuid
from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field, ValidationError, model_validator

from app.canais.base import (
    Acao,
    Anexo,
    ArquivoBaixado,
    ArquivoGrandeDemais,
    CredencialInvalida,
    DestinoInvalido,
    EntradaWebhook,
    Evento,
)
from app.canais.waha import api
from app.canais.waha.assinatura import assinatura_confere
from app.plataforma.textos import slug

COMANDO_RETOMAR = re.compile(r"^\s*/retomar\s+([A-Za-z0-9]{4,12})\s*$", re.IGNORECASE)
SUFIXOS_DE_PESSOA = ("@c.us", "@lid", "@s.whatsapp.net")
SUFIXO_DE_GRUPO = "@g.us"
JOINHA = "\U0001f44d"
"""Reagir com joinha numa mensagem devolve a conversa ao agente: é o que a pessoa tem à mão no
celular, sem precisar do código. Tons de pele e o seletor de variação entram na comparação."""
ENFEITES_DO_EMOJI = str.maketrans("", "", "\ufe0f\ufe0e" + "".join(chr(c) for c in range(0x1F3FB, 0x1F400)))


def e_joinha(texto: str | None) -> bool:
    return bool(texto) and str(texto).translate(ENFEITES_DO_EMOJI).strip() == JOINHA


class CredenciaisWaha(BaseModel):
    """O que fica guardado (cifrado). A chave da WAHA não entra: é da instalação, vem do `.env`."""

    sessao: str
    hmac_key: str


class DestinoWaha(BaseModel):
    """Quem recebe o aviso de handoff: um número de WhatsApp ou um grupo."""

    tipo: Literal["numero", "grupo"]
    chat_id: str = ""
    telefone: str | None = None
    nome: str | None = Field(default=None, max_length=200)

    @model_validator(mode="after")
    def _normaliza(self) -> "DestinoWaha":
        if self.tipo == "grupo":
            if not self.chat_id.endswith(SUFIXO_DE_GRUPO):
                raise ValueError("id de grupo inválido")
            self.telefone = None
            return self
        digitos = re.sub(r"\D", "", self.telefone or self.chat_id)
        if not 10 <= len(digitos) <= 15:
            raise ValueError("número inválido")
        self.chat_id = f"{digitos}@c.us"
        self.telefone = digitos
        return self


def _texto_do_destino(destino: dict[str, Any] | None) -> str | None:
    chat_id = (destino or {}).get("chat_id")
    return chat_id if isinstance(chat_id, str) and chat_id else None


def numero_legivel(chat_id: str) -> str:
    """`5511988887777@c.us` vira `+55 11 98888-7777`. O que não for número volta como veio."""
    digitos = chat_id.split("@")[0]
    if not digitos.isdigit():
        return chat_id
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        ddd, resto = digitos[2:4], digitos[4:]
        return f"+55 {ddd} {resto[:-4]}-{resto[-4:]}"
    return f"+{digitos}"


TIPOS_POR_MIME = (("audio/", "audio"), ("image/", "imagem"), ("video/", "video"))


def _anexos(mensagem: dict[str, Any]) -> tuple[Anexo, ...]:
    """A WAHA baixa o arquivo e devolve a URL dele em `media.url` (serviço local, com a chave)."""
    midia = mensagem.get("media")
    if not mensagem.get("hasMedia") or not isinstance(midia, dict):
        return ()
    url = midia.get("url")
    if not isinstance(url, str) or not url.startswith(("http://", "https://")):
        return ()
    mime = str(midia.get("mimetype") or "").split(";")[0].strip().lower()
    tipo = next((nome for prefixo, nome in TIPOS_POR_MIME if mime.startswith(prefixo)), "documento")
    return (
        Anexo(
            tipo=tipo,
            referencia=url,
            tipo_mime=mime or None,
            nome=midia.get("filename") if isinstance(midia.get("filename"), str) else None,
        ),
    )


def _chat_da_mensagem(mensagem: dict[str, Any]) -> str | None:
    """A conversa é sempre a do outro lado: no que sai do número, `from` é o próprio agente."""
    lado = mensagem.get("to") if mensagem.get("fromMe") else mensagem.get("from")
    lado = lado or mensagem.get("from")
    return lado if isinstance(lado, str) and lado else None


def _nome_do_contato(mensagem: dict[str, Any]) -> str | None:
    dados = mensagem.get("_data") if isinstance(mensagem.get("_data"), dict) else {}
    for campo in ("notifyName", "pushName", "senderName"):
        valor = mensagem.get(campo) or dados.get(campo)
        if isinstance(valor, str) and valor.strip():
            return valor.strip()
    return None


class Waha:
    nome = "waha"
    campos_secretos = frozenset({"hmac_key"})
    responde_200_em_assinatura_invalida = False
    retoma_por_tempo = True
    pede_acesso_do_operador = False
    externo = True
    webhook_interno = True

    # ── Conexão ────────────────────────────────────────────────────────────

    def acesso_do_operador(self, dados: dict[str, Any]) -> dict[str, Any]:
        return {}

    def endereco(self, dados: dict[str, Any]) -> str:
        return api.raiz()

    async def descobrir(self, dados: dict[str, Any]) -> dict[str, Any]:
        """Nada a escolher antes de conectar: a sessão nasce na criação do agente."""
        return {}

    async def conectar(
        self, dados: dict[str, Any], url_webhook: str, nome_agente: str
    ) -> dict[str, Any]:
        """Cria a sessão e a inicia. O pareamento (QR code) é conferido depois, pelo setup."""
        sessao = f"{slug(nome_agente)[:24] or 'agente'}-{uuid.uuid4().hex[:6]}"
        chave = secrets.token_hex(32)
        await api.cria_sessao(sessao, url_webhook, chave)
        return CredenciaisWaha(sessao=sessao, hmac_key=chave).model_dump()

    async def desconectar(self, dados: dict[str, Any], credenciais: dict[str, Any]) -> None:
        """Logout tira o aparelho da lista do WhatsApp; depois a sessão é apagada."""
        sessao = credenciais.get("sessao")
        if not sessao:
            return
        await api.sai_do_whatsapp(sessao)
        await api.apaga_sessao(sessao)

    async def renomear(self, dados: dict[str, Any], credenciais: dict[str, Any], nome: str) -> None:
        """No WhatsApp o nome é o do próprio número, mudado no aparelho: nada a fazer aqui."""
        return None

    # ── Webhook ────────────────────────────────────────────────────────────

    def verificar(self, entrada: EntradaWebhook, credenciais: dict[str, Any]) -> bool:
        return assinatura_confere(
            credenciais.get("hmac_key", ""),
            entrada.cabecalhos.get("x-webhook-hmac", ""),
            entrada.corpo,
        )

    def interpretar(
        self, payload: dict[str, Any], credenciais: dict[str, Any], destino: dict[str, Any] | None = None
    ) -> Evento:
        evento = payload.get("event")
        if evento not in ("message.any", "message", "message.reaction"):
            return Evento(Acao.IGNORAR, f"evento fora da lista: {evento!r}")
        sessao = payload.get("session")
        if sessao and credenciais.get("sessao") and sessao != credenciais["sessao"]:
            return Evento(Acao.IGNORAR, f"sessão de outro agente: {sessao!r}")

        mensagem = payload.get("payload")
        if not isinstance(mensagem, dict):
            return Evento(Acao.IGNORAR, "webhook sem mensagem")

        chat = _chat_da_mensagem(mensagem)
        if chat is None:
            return Evento(Acao.IGNORAR, "mensagem sem conversa")

        if evento == "message.reaction":
            return self._reacao(mensagem, chat)

        if mensagem.get("fromMe"):
            return self._saiu_do_numero(mensagem, chat)

        texto = mensagem.get("body") if isinstance(mensagem.get("body"), str) else None
        chat_do_destino = _texto_do_destino(destino)
        comando = COMANDO_RETOMAR.match(texto or "")
        if chat == chat_do_destino and comando:
            return Evento(
                Acao.RETOMAR_POR_CODIGO,
                "quem recebeu o handoff mandou /retomar",
                codigo=comando.group(1).upper(),
            )
        if chat.endswith(SUFIXO_DE_GRUPO):
            return Evento(Acao.IGNORAR, "mensagem de grupo")
        if not chat.endswith(SUFIXOS_DE_PESSOA):
            return Evento(Acao.IGNORAR, f"conversa que o agente não atende: {chat!r}")

        base: dict[str, Any] = {
            "conversa_externa": chat,
            "contato_externo": chat,
            "contato_nome": _nome_do_contato(mensagem),
            "contato_telefone": chat.split("@")[0] if chat.endswith("@c.us") else None,
            "mensagem_externa": str(mensagem.get("id")) if mensagem.get("id") is not None else None,
            "texto": texto,
            "anexos": _anexos(mensagem),
        }
        if comando:
            # Código certo, número errado: vira conversa comum, como qualquer outra mensagem.
            return Evento(Acao.PROCESSAR, "mensagem do contato (/retomar de outro número)", **base)
        if not (texto or "").strip() and not base["anexos"]:
            return Evento(Acao.REGISTRAR, "mensagem sem conteúdo", **base)
        return Evento(Acao.PROCESSAR, "mensagem do contato", **base)

    def _reacao(self, mensagem: dict[str, Any], chat: str) -> Evento:
        """Joinha do número do agente devolve a conversa; reação do contato não mexe em nada."""
        reacao = mensagem.get("reaction")
        emoji = reacao.get("text") if isinstance(reacao, dict) else None
        if not mensagem.get("fromMe"):
            return Evento(Acao.IGNORAR, "reação do contato", chat)
        if not e_joinha(emoji):
            return Evento(Acao.IGNORAR, f"reação que não é joinha: {emoji!r}", chat)
        if chat.endswith(SUFIXO_DE_GRUPO):
            return Evento(Acao.IGNORAR, "reação em grupo", chat)
        return Evento(Acao.RETOMAR, "joinha devolveu a conversa ao agente", chat, por="joinha")

    def _saiu_do_numero(self, mensagem: dict[str, Any], chat: str) -> Evento:
        """Mensagem do próprio número: ou foi o agente pela API, ou é gente digitando no aparelho.

        `source` da WAHA separa os dois: `api` é o agente falando, `app` é uma pessoa da empresa
        que abriu o WhatsApp e respondeu. Nesse caso o agente cala até o joinha ou o prazo.
        """
        if mensagem.get("source") == "api":
            return Evento(Acao.IGNORAR, "mensagem enviada pelo próprio agente", chat)
        if chat.endswith(SUFIXO_DE_GRUPO):
            return Evento(Acao.IGNORAR, "mensagem de grupo", chat)
        texto = mensagem.get("body") if isinstance(mensagem.get("body"), str) else None
        return Evento(
            Acao.PAUSAR,
            "uma pessoa respondeu pelo aparelho",
            conversa_externa=chat,
            mensagem_externa=str(mensagem.get("id")) if mensagem.get("id") is not None else None,
            texto=texto,
            anexos=_anexos(mensagem),
            autor="humano",
            direcao="saida",
        )

    # ── Operação ───────────────────────────────────────────────────────────

    async def agente_pode_falar(
        self, credenciais: dict[str, Any], conversa_externa: str, status: str
    ) -> bool:
        """No WhatsApp direto não há onde perguntar: a pausa do handoff é o status da conversa."""
        return status != "humano"

    async def digitando(
        self, credenciais: dict[str, Any], conversa_externa: str, ligado: bool
    ) -> None:
        if ligado:
            await api.marca_lida(credenciais["sessao"], conversa_externa)
        await api.digitando(credenciais["sessao"], conversa_externa, ligado)

    async def enviar_texto(
        self, credenciais: dict[str, Any], conversa_externa: str, texto: str
    ) -> str | None:
        return await api.envia_texto(credenciais["sessao"], conversa_externa, texto)

    def valida_destino_handoff(self, destino: dict[str, Any] | None) -> dict[str, Any] | None:
        if destino is None:
            return None
        try:
            return DestinoWaha.model_validate(destino).model_dump()
        except ValidationError as erro:
            raise DestinoInvalido(
                "destino de handoff da WAHA deve ser um número de WhatsApp com DDI e DDD ou um grupo"
            ) from erro

    async def transferir(
        self,
        credenciais: dict[str, Any],
        conversa_externa: str,
        destino: dict[str, Any] | None,
        nota: str,
        codigo: str = "",
    ) -> list[str]:
        """Avisa o número ou grupo do handoff. A pausa é o status da conversa, gravado por quem chama."""
        chat = _texto_do_destino(destino)
        if chat is None:
            return ["agente sem destino de handoff: ninguém foi avisado"]
        aviso = (
            f"Assumi a conversa com {numero_legivel(conversa_externa)} e o agente parou de responder.\n\n"
            f"{nota}\n\n"
            f"Quando terminar, devolva ao agente: reaja com {JOINHA} em qualquer mensagem da conversa "
            f"ou mande /retomar {codigo} aqui."
        )
        try:
            await api.envia_texto(credenciais["sessao"], chat, aviso)
        except Exception as erro:
            return [f"aviso de handoff não chegou: {type(erro).__name__}"]
        return []

    def rotulo_da_conversa(self, conversa_externa: str) -> str:
        return numero_legivel(conversa_externa)

    async def avisa_destino(
        self, credenciais: dict[str, Any], destino: dict[str, Any] | None, texto: str
    ) -> None:
        chat = _texto_do_destino(destino)
        if chat is not None:
            await api.envia_texto(credenciais["sessao"], chat, texto)

    async def devolver_ao_agente(self, credenciais: dict[str, Any], conversa_externa: str) -> None:
        """A conversa volta pelo status aqui; no WhatsApp não há nada para desfazer."""
        return None

    async def baixar_midia(
        self, credenciais: dict[str, Any], anexo: Anexo, limite_bytes: int
    ) -> ArquivoBaixado:
        """A URL é do serviço de arquivos da própria WAHA: vai com a chave da instalação."""
        partes: list[bytes] = []
        total = 0
        try:
            async with httpx.AsyncClient(
                timeout=api.TIMEOUT_DOWNLOAD, headers=api.cabecalho(), follow_redirects=True
            ) as http:
                async with http.stream("GET", anexo.referencia) as resposta:
                    resposta.raise_for_status()
                    async for parte in resposta.aiter_bytes():
                        total += len(parte)
                        if total > limite_bytes:
                            raise ArquivoGrandeDemais(f"mais de {limite_bytes} bytes")
                        partes.append(parte)
                    mime = resposta.headers.get("content-type", "").split(";")[0].strip().lower()
        except httpx.HTTPError as erro:
            raise CredencialInvalida(f"não consegui baixar o arquivo na WAHA ({type(erro).__name__})") from erro
        if not mime or mime == "application/octet-stream":
            mime = anexo.tipo_mime or mime
        return ArquivoBaixado(conteudo=b"".join(partes), tipo_mime=mime or "application/octet-stream")
