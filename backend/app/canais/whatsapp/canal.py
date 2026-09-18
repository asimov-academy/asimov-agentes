"""Canal WhatsApp oficial: um número da Cloud API da Meta por agente.

Cada agente tem o próprio endereço de webhook, apontado no número pelo `webhook_configuration`
(webhook override da Meta): assim um app da Meta atende vários números sem misturar agentes. A
verificação (`hub.challenge`) é respondida pelo próprio token da URL, que já é o segredo do
webhook; o corpo vem assinado com o `app_secret` em `X-Hub-Signature-256`.

Diferenças para a WAHA, que este arquivo respeita:
- não existe "gente respondendo pelo aparelho": o número da Cloud API não roda no celular, então
  não há pausa por intervenção nem joinha na conversa do contato;
- o aviso de handoff quase sempre sai como template aprovado, porque a Meta só deixa escrever
  livremente até 24 h depois da última mensagem de quem vai receber;
- a devolução é `/retomar` (ou 👍 no aviso) escrita pelo destino no chat dele com o número do
  agente, ou o prazo do agente.
"""

import re
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
from app.canais.whatsapp import api
from app.canais.whatsapp.assinatura import assinatura_confere
from app.plataforma.textos import mesmo_telefone, so_digitos, telefone_legivel

COMANDO_RETOMAR = re.compile(r"^\s*/retomar(?:\s+([A-Za-z0-9]{4,12}))?\s*$", re.IGNORECASE)
JOINHA = "\U0001f44d"
ENFEITES_DO_EMOJI = str.maketrans(
    "", "", "️︎" + "".join(chr(c) for c in range(0x1F3FB, 0x1F400))
)

TIPOS_DE_ANEXO = {
    "audio": "audio",
    "voice": "audio",
    "image": "imagem",
    "video": "video",
    "sticker": "imagem",
    "document": "documento",
}
PARAMETROS_DO_TEMPLATE = 3
"""Contato, resumo e código: o que o aviso de handoff precisa dizer."""
LIMITE_DO_PARAMETRO = 700
"""A Meta recusa parâmetro com quebra de linha ou muito longo."""


def e_joinha(texto: str | None) -> bool:
    return bool(texto) and str(texto).translate(ENFEITES_DO_EMOJI).strip() == JOINHA


class CredenciaisWhatsApp(BaseModel):
    """O que fica guardado (cifrado). O token e o segredo do app nunca saem da API."""

    waba_id: str
    phone_number_id: str
    app_id: str
    access_token: str
    app_secret: str
    numero: str = ""
    """Número como a Meta mostra (`+55 11 98888-7777`), só para o menu."""
    nome_verificado: str = ""


class TemplateHandoff(BaseModel):
    nome: str = Field(min_length=1, max_length=200)
    idioma: str = Field(min_length=2, max_length=20)


class DestinoWhatsApp(BaseModel):
    """Quem recebe o aviso de handoff: um número de WhatsApp, e o template que leva o aviso.

    O template mora aqui, e não no agente, porque é como se avisa o destino neste canal: fora da
    janela de 24 horas a Meta não aceita outra coisa.
    """

    tipo: Literal["numero"] = "numero"
    telefone: str
    template: TemplateHandoff | None = None

    @model_validator(mode="after")
    def _normaliza(self) -> "DestinoWhatsApp":
        digitos = so_digitos(self.telefone)
        if not 10 <= len(digitos) <= 15:
            raise ValueError("número inválido")
        self.telefone = digitos
        return self


def _texto_do_destino(destino: dict[str, Any] | None) -> str | None:
    telefone = (destino or {}).get("telefone")
    return str(telefone) if telefone else None


def _para_o_template(texto: str) -> str:
    """Parâmetro de template não aceita quebra de linha nem espaço em excesso."""
    limpo = re.sub(r"\s+", " ", texto).strip()
    return limpo[:LIMITE_DO_PARAMETRO] if limpo else "-"


# ── Leitura do webhook ─────────────────────────────────────────────────────


def _mudancas(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """A Meta embrulha tudo em `entry[].changes[].value`. Só interessa o campo `messages`.

    Devolve todas: um envelope pode trazer várias entradas e várias mudanças, e ler só a primeira
    perdia mensagem com o webhook confirmado (auditoria de 2026-09-18, A08).
    """
    achadas: list[dict[str, Any]] = []
    entradas = payload.get("entry")
    if not isinstance(entradas, list):
        return achadas
    for entrada in entradas:
        mudancas = entrada.get("changes") if isinstance(entrada, dict) else None
        if not isinstance(mudancas, list):
            continue
        for mudanca in mudancas:
            if isinstance(mudanca, dict) and mudanca.get("field") == "messages":
                valor = mudanca.get("value")
                if isinstance(valor, dict):
                    achadas.append(valor)
    return achadas


def _mudanca(payload: dict[str, Any]) -> dict[str, Any] | None:
    mudancas = _mudancas(payload)
    return mudancas[0] if mudancas else None


def _nome_do_contato(valor: dict[str, Any], de: str) -> str | None:
    contatos = valor.get("contacts")
    if not isinstance(contatos, list):
        return None
    for contato in contatos:
        if not isinstance(contato, dict):
            continue
        if contato.get("wa_id") and str(contato["wa_id"]) != de:
            continue
        perfil = contato.get("profile")
        nome = perfil.get("name") if isinstance(perfil, dict) else None
        if isinstance(nome, str) and nome.strip():
            return nome.strip()
    return None


def _anexo(mensagem: dict[str, Any]) -> Anexo | None:
    """O arquivo fica na Meta: o que chega é o id, baixado depois, no turno."""
    tipo = str(mensagem.get("type") or "")
    nosso_tipo = TIPOS_DE_ANEXO.get(tipo)
    if nosso_tipo is None:
        return None
    dados = mensagem.get(tipo)
    if not isinstance(dados, dict) or not dados.get("id"):
        return None
    return Anexo(
        tipo=nosso_tipo,
        referencia=str(dados["id"]),
        tipo_mime=str(dados.get("mime_type") or "").split(";")[0].strip().lower() or None,
        nome=dados.get("filename") if isinstance(dados.get("filename"), str) else None,
    )


def _texto(mensagem: dict[str, Any]) -> str | None:
    """Texto, legenda de mídia ou o rótulo do botão que o contato apertou."""
    tipo = str(mensagem.get("type") or "")
    if tipo == "text":
        corpo = mensagem.get("text")
        return corpo.get("body") if isinstance(corpo, dict) else None
    if tipo == "button":
        corpo = mensagem.get("button")
        return corpo.get("text") if isinstance(corpo, dict) else None
    if tipo == "interactive":
        corpo = mensagem.get("interactive")
        if isinstance(corpo, dict):
            escolha = corpo.get(str(corpo.get("type") or ""))
            if isinstance(escolha, dict):
                return escolha.get("title") or escolha.get("description")
        return None
    dados = mensagem.get(tipo)
    legenda = dados.get("caption") if isinstance(dados, dict) else None
    return legenda if isinstance(legenda, str) else None


class WhatsApp:
    nome = "whatsapp"
    campos_secretos = frozenset({"access_token", "app_secret"})
    responde_200_em_assinatura_invalida = False
    retoma_por_tempo = True
    pede_acesso_do_operador = False
    externo = True
    webhook_interno = False

    # ── Conexão ────────────────────────────────────────────────────────────

    def acesso_do_operador(self, dados: dict[str, Any]) -> dict[str, Any]:
        """O token de acesso é do agente, não da instalação: não há acesso guardado por aqui."""
        return {}

    def endereco(self, dados: dict[str, Any]) -> str:
        return f"{api.GRAPH}/{dados.get('waba_id') or '?'}"

    async def descobrir(self, dados: dict[str, Any]) -> dict[str, Any]:
        """Sem a conta, descobre quais o token alcança. Com a conta, lista números e templates.

        O ID da conta é o dado mais escondido do painel da Meta. Em vez de mandar o operador
        procurar, o primeiro passo pergunta ao próprio token quais contas ele enxerga.
        """
        token = str(dados.get("access_token") or "")
        if not token:
            raise CredencialInvalida("informe o token de acesso")
        conta = str(dados.get("waba_id") or "")
        if not conta:
            app_id = str(dados.get("app_id") or "")
            app_secret = str(dados.get("app_secret") or "")
            if not app_id or not app_secret:
                raise CredencialInvalida("informe o ID e a chave secreta do app")
            return {"contas": await api.contas_do_token(app_id, app_secret, token)}
        numeros = await api.numeros_da_conta(token, conta)
        todos = await api.templates(token, conta)
        return {
            "numeros": numeros,
            "templates": [
                t
                for t in todos
                if t["situacao"] == "APPROVED" and t["parametros"] == PARAMETROS_DO_TEMPLATE
            ],
            "templates_todos": todos,
        }

    async def conectar(
        self, dados: dict[str, Any], url_webhook: str, nome_agente: str
    ) -> dict[str, Any]:
        """Confere o número, inscreve o app e aponta os webhooks daquele número para esta URL.

        A Meta chama a URL na hora, com `hub.challenge`; quem responde é `responde_verificacao`,
        pelo token que já está no endereço.
        """
        credenciais = self._credenciais(dados)
        ficha = await api.numero(credenciais.access_token, credenciais.phone_number_id)
        credenciais.numero = ficha["numero"]
        credenciais.nome_verificado = ficha["nome"]
        token_do_webhook = url_webhook.rstrip("/").rsplit("/", 1)[-1]
        # Três camadas, nesta ordem: o app assina o campo `messages`, a conta passa a entregar a
        # este app e o número ganha o endereço deste agente. Sem a primeira, nada chega.
        await api.liga_webhook_do_app(
            credenciais.app_id, credenciais.app_secret, url_webhook, token_do_webhook
        )
        await api.inscreve_app(credenciais.access_token, credenciais.waba_id)
        await api.aponta_webhook(
            credenciais.access_token, credenciais.phone_number_id, url_webhook, token_do_webhook
        )
        return credenciais.model_dump()

    def _credenciais(self, dados: dict[str, Any]) -> CredenciaisWhatsApp:
        try:
            return CredenciaisWhatsApp.model_validate(dados)
        except ValidationError as erro:
            faltando = ", ".join(sorted({str(e["loc"][0]) for e in erro.errors()}))
            raise CredencialInvalida(
                f"faltam dados do WhatsApp oficial: {faltando}"
            ) from erro

    async def desconectar(self, dados: dict[str, Any], credenciais: dict[str, Any]) -> None:
        """Devolve os webhooks do número para a URL do app. O número segue existindo na Meta."""
        if not credenciais.get("phone_number_id"):
            return
        await api.limpa_webhook(credenciais["access_token"], credenciais["phone_number_id"])

    async def renomear(self, dados: dict[str, Any], credenciais: dict[str, Any], nome: str) -> None:
        """Quem aparece para o contato é o nome verificado do número, que se muda na Meta."""
        return None

    # ── Webhook ────────────────────────────────────────────────────────────

    def responde_verificacao(self, parametros: dict[str, str], token: str) -> str | None:
        """`GET` de verificação da Meta: devolve o desafio quando o token confere."""
        if parametros.get("hub.mode") != "subscribe":
            return None
        if not token or parametros.get("hub.verify_token") != token:
            return None
        return parametros.get("hub.challenge") or ""

    def verificar(self, entrada: EntradaWebhook, credenciais: dict[str, Any]) -> bool:
        return assinatura_confere(
            credenciais.get("app_secret", ""),
            entrada.cabecalhos.get("x-hub-signature-256", ""),
            entrada.corpo,
        )

    def interpretar(
        self,
        payload: dict[str, Any],
        credenciais: dict[str, Any],
        destino: dict[str, Any] | None = None,
    ) -> Evento:
        """O primeiro evento do envelope. Quem processa tudo é `interpretar_todos`."""
        return self.interpretar_todos(payload, credenciais, destino)[0]

    def interpretar_todos(
        self,
        payload: dict[str, Any],
        credenciais: dict[str, Any],
        destino: dict[str, Any] | None = None,
    ) -> list[Evento]:
        """Um envelope da Cloud API pode trazer várias mensagens; cada uma vira um evento."""
        if payload.get("object") != "whatsapp_business_account":
            return [Evento(Acao.IGNORAR, f"webhook fora da lista: {payload.get('object')!r}")]

        eventos: list[Evento] = []
        vazio = Evento(Acao.IGNORAR, "webhook sem mensagem")
        for valor in _mudancas(payload):
            metadados = valor.get("metadata")
            numero_do_webhook = metadados.get("phone_number_id") if isinstance(metadados, dict) else None
            meu = credenciais.get("phone_number_id")
            if numero_do_webhook and meu and str(numero_do_webhook) != str(meu):
                vazio = Evento(Acao.IGNORAR, f"número de outro agente: {numero_do_webhook!r}")
                continue
            if valor.get("statuses"):
                vazio = self._entrega(valor)
                continue
            mensagens = valor.get("messages")
            if not isinstance(mensagens, list):
                continue
            for mensagem in mensagens:
                if isinstance(mensagem, dict):
                    eventos.append(self._evento_da_mensagem(valor, mensagem, destino))
        return eventos or [vazio]

    def _entrega(self, valor: dict[str, Any]) -> Evento:
        """Recibo de entrega. `failed` vira falha visível: a mensagem não chegou ao contato.

        A Meta avisa a recusa por aqui, depois de aceitar o envio, e antes isso era descartado
        junto com o recibo comum (auditoria de 2026-09-18, A07).
        """
        for status in valor.get("statuses") or []:
            if not isinstance(status, dict) or status.get("status") != "failed":
                continue
            erros = status.get("errors")
            primeiro = erros[0] if isinstance(erros, list) and erros and isinstance(erros[0], dict) else {}
            return Evento(
                Acao.ENTREGA_RECUSADA,
                f"a Meta recusou a entrega: {primeiro.get('title') or primeiro.get('message') or 'sem detalhe'}",
                texto=str(primeiro.get("code") or ""),
                mensagem_externa=str(status.get("id")) if status.get("id") else None,
            )
        return Evento(Acao.IGNORAR, "recibo de entrega da própria mensagem")

    def _evento_da_mensagem(
        self, valor: dict[str, Any], mensagem: dict[str, Any], destino: dict[str, Any] | None
    ) -> Evento:
        de = str(mensagem.get("from") or "")
        if not de:
            return Evento(Acao.IGNORAR, "mensagem sem remetente")

        if mensagem.get("type") == "reaction":
            return self._reacao(mensagem, de, destino)

        texto = _texto(mensagem)
        comando = COMANDO_RETOMAR.match(texto or "")
        do_destino = self._e_o_destino(de, destino)
        if comando and do_destino:
            codigo = comando.group(1)
            return Evento(
                Acao.RETOMAR_POR_CODIGO,
                "quem recebeu o handoff mandou /retomar",
                codigo=codigo.upper() if codigo else None,
            )

        anexo = _anexo(mensagem)
        base: dict[str, Any] = {
            "conversa_externa": de,
            "contato_externo": de,
            "contato_nome": _nome_do_contato(valor, de),
            "contato_telefone": so_digitos(de),
            "mensagem_externa": str(mensagem.get("id")) if mensagem.get("id") else None,
            "texto": texto,
            "anexos": (anexo,) if anexo else (),
        }
        if comando:
            # Código certo, número errado: vira conversa comum, como qualquer outra mensagem.
            return Evento(Acao.PROCESSAR, "mensagem do contato (/retomar de outro número)", **base)
        if not (texto or "").strip() and not base["anexos"]:
            return Evento(
                Acao.REGISTRAR, f"mensagem sem conteúdo que o agente leia ({mensagem.get('type')})", **base
            )
        return Evento(Acao.PROCESSAR, "mensagem do contato", **base)

    def _e_o_destino(self, de: str, destino: dict[str, Any] | None) -> bool:
        telefone = _texto_do_destino(destino)
        return bool(telefone) and mesmo_telefone(str(telefone), de)

    def _reacao(
        self, mensagem: dict[str, Any], de: str, destino: dict[str, Any] | None
    ) -> Evento:
        """👍 de quem recebeu o aviso devolve a conversa; reação do contato não mexe em nada."""
        reacao = mensagem.get("reaction")
        emoji = reacao.get("emoji") if isinstance(reacao, dict) else None
        if not self._e_o_destino(de, destino):
            return Evento(Acao.IGNORAR, "reação do contato", de)
        if not e_joinha(emoji):
            return Evento(Acao.IGNORAR, f"reação que não é joinha: {emoji!r}", de)
        return Evento(Acao.RETOMAR_POR_CODIGO, "joinha de quem recebeu o handoff", por="joinha")

    # ── Operação ───────────────────────────────────────────────────────────

    async def agente_pode_falar(
        self, credenciais: dict[str, Any], conversa_externa: str, status: str
    ) -> bool:
        """No WhatsApp direto não há onde perguntar: a pausa do handoff é o status da conversa."""
        return status != "humano"

    async def digitando(
        self,
        credenciais: dict[str, Any],
        conversa_externa: str,
        ligado: bool,
        ultima_mensagem: str | None = None,
    ) -> None:
        """Na Cloud API o digitando é preso à mensagem que chegou, e some sozinho em 25 s."""
        if not ligado or not ultima_mensagem:
            return
        await api.digitando(
            credenciais["access_token"], credenciais["phone_number_id"], ultima_mensagem
        )

    async def enviar_texto(
        self, credenciais: dict[str, Any], conversa_externa: str, texto: str
    ) -> str | None:
        return await api.envia_texto(
            credenciais["access_token"], credenciais["phone_number_id"], conversa_externa, texto
        )

    def valida_destino_handoff(self, destino: dict[str, Any] | None) -> dict[str, Any] | None:
        if destino is None:
            return None
        try:
            return DestinoWhatsApp.model_validate(destino).model_dump()
        except ValidationError as erro:
            raise DestinoInvalido(
                "destino de handoff do WhatsApp oficial deve ser um número com DDI e DDD, e o"
                " template aprovado que leva o aviso"
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
        """Avisa o número do handoff. A pausa é o status da conversa, gravado por quem chama."""
        telefone = _texto_do_destino(destino)
        if telefone is None:
            return ["agente sem destino de handoff: ninguém foi avisado"]
        quem = contato or self.rotulo_da_conversa(conversa_externa)
        aviso = (
            f"Assumi a conversa com {quem} e o agente parou de responder.\n\n"
            f"{nota}\n\n"
            f"Quando terminar, devolva ao agente de um destes jeitos:\n"
            f"1) reaja com {JOINHA} nesta mensagem;\n"
            f"2) responda /retomar aqui (com mais de uma conversa em atendimento: /retomar {codigo})."
        )
        try:
            await api.envia_texto(
                credenciais["access_token"], credenciais["phone_number_id"], telefone, aviso
            )
        except api.ForaDaJanela:
            return await self._aviso_por_template(credenciais, destino, quem, nota, codigo)
        except Exception as erro:
            return [f"aviso de handoff não chegou para +{telefone}: {erro}"]
        return []

    async def _aviso_por_template(
        self,
        credenciais: dict[str, Any],
        destino: dict[str, Any],
        quem: str,
        nota: str,
        codigo: str,
    ) -> list[str]:
        """Fora da janela de 24 h a Meta só aceita template aprovado, com os dados como parâmetros."""
        template = destino.get("template")
        telefone = str(destino.get("telefone"))
        if not isinstance(template, dict) or not template.get("nome"):
            return [
                f"+{telefone} não fala com este número há mais de 24 horas e o agente não tem"
                " template de aviso: escolha um em Editar agente, opção WhatsApp"
            ]
        try:
            await api.envia_template(
                credenciais["access_token"],
                credenciais["phone_number_id"],
                telefone,
                str(template["nome"]),
                str(template.get("idioma") or "pt_BR"),
                [_para_o_template(quem), _para_o_template(nota), codigo or "-"],
            )
        except Exception as erro:
            return [f"aviso de handoff não chegou para +{telefone} nem por template: {erro}"]
        return []

    def rotulo_da_conversa(self, conversa_externa: str) -> str:
        return telefone_legivel(conversa_externa.split("@")[0]) or conversa_externa

    async def avisa_destino(
        self, credenciais: dict[str, Any], destino: dict[str, Any] | None, texto: str
    ) -> None:
        """Recado curto ao destino. Fora da janela de 24 h a Meta recusa, e aí não há o que fazer:
        template é mensagem de aviso de handoff, não de conversa."""
        telefone = _texto_do_destino(destino)
        if telefone is None:
            return
        try:
            await api.envia_texto(
                credenciais["access_token"], credenciais["phone_number_id"], telefone, texto
            )
        except api.ForaDaJanela:
            return

    async def devolver_ao_agente(self, credenciais: dict[str, Any], conversa_externa: str) -> None:
        """A conversa volta pelo status aqui; no WhatsApp não há nada para desfazer."""
        return None

    async def assumir_no_canal(
        self, credenciais: dict[str, Any], conversa_externa: str, autor_externo: str | None
    ) -> None:
        """No WhatsApp a conversa não tem dono: quem assumiu já está respondendo por ela."""
        return None

    async def baixar_midia(
        self, credenciais: dict[str, Any], anexo: Anexo, limite_bytes: int
    ) -> ArquivoBaixado:
        """Dois passos: o id vira URL na Graph API, e a URL abre com o mesmo token."""
        token = credenciais["access_token"]
        endereco = await api.endereco_da_midia(token, anexo.referencia)
        if not endereco["url"]:
            raise CredencialInvalida("a Meta não devolveu o endereço do arquivo")
        if endereco["tamanho"] and endereco["tamanho"] > limite_bytes:
            raise ArquivoGrandeDemais(f"mais de {limite_bytes} bytes")
        partes: list[bytes] = []
        total = 0
        try:
            async with httpx.AsyncClient(
                timeout=api.TIMEOUT_DOWNLOAD,
                headers={"Authorization": f"Bearer {token}"},
                follow_redirects=True,
            ) as http:
                async with http.stream("GET", endereco["url"]) as resposta:
                    resposta.raise_for_status()
                    async for parte in resposta.aiter_bytes():
                        total += len(parte)
                        if total > limite_bytes:
                            raise ArquivoGrandeDemais(f"mais de {limite_bytes} bytes")
                        partes.append(parte)
                    mime = resposta.headers.get("content-type", "").split(";")[0].strip().lower()
        except httpx.HTTPStatusError as erro:
            raise CredencialInvalida(
                f"a Meta recusou o arquivo: HTTP {erro.response.status_code}"
            ) from erro
        except httpx.HTTPError as erro:
            raise CredencialInvalida(
                f"não consegui baixar o arquivo na Meta ({type(erro).__name__})"
            ) from erro
        if not mime or mime == "application/octet-stream":
            mime = endereco["tipo_mime"] or anexo.tipo_mime or mime
        return ArquivoBaixado(conteudo=b"".join(partes), tipo_mime=mime or "application/octet-stream")
