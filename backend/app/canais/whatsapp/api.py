"""Chamadas à Cloud API da Meta (Graph API), o WhatsApp oficial.

Cada agente tem um número (`phone_number_id`) de uma conta de WhatsApp Business (`waba_id`), com
um token de acesso permanente e o `app_secret` do app da Meta, tudo guardado cifrado nas
credenciais do agente. Não há chave da instalação aqui: cada empresa tem o próprio app.

Endpoints conferidos na documentação da Meta (2026-09-18):
- `GET /debug_token` e `GET /me/businesses` descobrem as contas de WhatsApp Business que o token
  alcança, para o operador não ter de achar o WABA ID no painel;
- `GET /{waba_id}/phone_numbers` lista os números da conta; `GET /{waba_id}/message_templates`
  lista os templates, com o idioma e a situação da aprovação;
- `POST /{app_id}/subscriptions` liga os webhooks do app (objeto `whatsapp_business_account`,
  campo `messages`), com o token do app (`{app_id}|{app_secret}`). Sem isso a Meta não entrega
  nada, nem para um endereço apontado no número;
- `POST /{waba_id}/subscribed_apps` inscreve o app nos webhooks da conta;
- `POST /{phone_number_id}` com `webhook_configuration` aponta os webhooks daquele número para uma
  URL própria (webhook override), que é o que deixa cada agente ter o próprio endereço;
- `POST /{phone_number_id}/messages` envia texto e template, marca como lida e liga o digitando
  (`status: read` com `typing_indicator`, que dura 25 s ou até a resposta sair);
- `GET /{media_id}` devolve a URL do arquivo, que é baixada com o mesmo token.
"""

from typing import Any

import httpx

from app.canais.base import CredencialInvalida

GRAPH = "https://graph.facebook.com"
VERSAO = "v23.0"
"""Versão da Graph API que esta versão do setup usa. A Meta mantém cada versão por cerca de dois
anos; subir de versão é trocar esta linha."""

TIMEOUT = httpx.Timeout(20.0, connect=5.0)
TIMEOUT_DOWNLOAD = httpx.Timeout(60.0, connect=5.0)

LIMITE_TEMPLATES = 200

CAMPOS_DO_WEBHOOK = "messages"
"""O que o agente lê: mensagens recebidas e reações. Recibo de entrega não serve para nada aqui e
só gastaria requisição."""
OBJETO_DO_WEBHOOK = "whatsapp_business_account"

CODIGOS_DE_TOKEN = (190,)
"""OAuthException: token errado, expirado ou sem permissão."""
CODIGOS_DE_OBJETO_SUMIDO = (100, 803)
"""Número ou conta que já não existe (ou que o token não enxerga mais): desconectar não falha por
isso, senão remover o agente ficaria preso a um número apagado na Meta."""
CODIGOS_FORA_DA_JANELA = (131047, 470)
"""A Meta só deixa escrever livremente até 24 h depois da última mensagem do contato; fora disso,
só template aprovado."""


class ForaDaJanela(CredencialInvalida):
    """Passaram-se mais de 24 horas: só template aprovado chega a esse número."""


def _raiz() -> str:
    return f"{GRAPH}/{VERSAO}"


def _http(token: str) -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=TIMEOUT, base_url=_raiz(), headers={"Authorization": f"Bearer {token}"}
    )


def _corpo(resposta: httpx.Response) -> Any:
    try:
        return resposta.json()
    except ValueError:
        return {}


def _detalhe(corpo: Any) -> tuple[int | None, str]:
    erro = corpo.get("error") if isinstance(corpo, dict) else None
    if not isinstance(erro, dict):
        return None, ""
    codigo = erro.get("code") if isinstance(erro.get("code"), int) else None
    texto = erro.get("error_user_msg") or erro.get("message") or ""
    return codigo, str(texto)


def _levanta(acao: str, resposta: httpx.Response) -> None:
    codigo, texto = _detalhe(_corpo(resposta))
    if codigo in CODIGOS_FORA_DA_JANELA:
        raise ForaDaJanela(texto or "passaram-se mais de 24 horas desde a última mensagem")
    if codigo in CODIGOS_DE_TOKEN or resposta.status_code == 401:
        raise CredencialInvalida(
            f"a Meta recusou o token de acesso: {texto or 'token inválido ou expirado'}"
        )
    raise CredencialInvalida(
        f"a Meta recusou {acao}: HTTP {resposta.status_code}{f' ({texto})' if texto else ''}"
    )


async def _chama(
    token: str,
    metodo: str,
    caminho: str,
    acao: str,
    json: dict[str, Any] | None = None,
    params: dict[str, Any] | None = None,
    ignora: tuple[int, ...] = (),
) -> dict[str, Any]:
    """`ignora` são códigos de erro da Meta que não são problema (objeto que já não existe)."""
    try:
        async with _http(token) as http:
            resposta = await http.request(metodo, caminho, json=json, params=params)
    except httpx.HTTPError as erro:
        raise CredencialInvalida(f"não consegui {acao} na Meta ({type(erro).__name__})") from erro
    if resposta.status_code >= 400:
        if _detalhe(_corpo(resposta))[0] in ignora:
            return {}
        _levanta(acao, resposta)
    corpo = _corpo(resposta)
    return corpo if isinstance(corpo, dict) else {}


# ── Conta e números ────────────────────────────────────────────────────────


ESCOPOS_DE_WHATSAPP = ("whatsapp_business_management", "whatsapp_business_messaging")


async def contas_do_token(app_id: str, app_secret: str, token: str) -> list[dict[str, Any]]:
    """Contas de WhatsApp Business que o token alcança, para o operador não procurar o WABA ID.

    O ID da conta é o dado mais escondido do painel da Meta, e errar ele é o erro mais comum de
    quem faz isso pela primeira vez. Dois caminhos, nesta ordem:

    1. `debug_token` devolve, em `granular_scopes`, os `target_ids` dos escopos de WhatsApp. É o
       caminho do token que foi gerado para contas específicas.
    2. token de usuário do sistema com controle do negócio inteiro não traz `target_ids`. Aí a
       conta sai dos negócios do token (`/me/businesses`), próprios e compartilhados.

    Lista vazia não é erro: o setup pergunta o ID à mão.
    """
    achadas: dict[str, str] = {}
    for waba_id in await _contas_do_escopo(app_id, app_secret, token):
        achadas[waba_id] = ""
    if not achadas:
        for conta in await _contas_dos_negocios(token):
            achadas[conta["waba_id"]] = conta["nome"]
    for waba_id, nome in list(achadas.items()):
        if not nome:
            achadas[waba_id] = await _nome_da_conta(token, waba_id)
    return [{"waba_id": i, "nome": n} for i, n in achadas.items()]


async def _contas_do_escopo(app_id: str, app_secret: str, token: str) -> list[str]:
    """Os `target_ids` dos escopos de WhatsApp no `debug_token`. Também prova que o token vale."""
    corpo = await _chama(
        f"{app_id}|{app_secret}",
        "GET",
        "/debug_token",
        "conferir o token de acesso",
        params={"input_token": token},
    )
    dados = corpo.get("data")
    escopos = dados.get("granular_scopes") if isinstance(dados, dict) else None
    encontrados: list[str] = []
    for escopo in escopos or []:
        if not isinstance(escopo, dict) or escopo.get("scope") not in ESCOPOS_DE_WHATSAPP:
            continue
        for alvo in escopo.get("target_ids") or []:
            if str(alvo) not in encontrados:
                encontrados.append(str(alvo))
    return encontrados


async def _contas_dos_negocios(token: str) -> list[dict[str, str]]:
    """Contas de WhatsApp dos negócios que o token alcança, próprias e compartilhadas.

    Falha aqui não derruba nada: o setup pergunta o ID à mão.
    """
    try:
        negocios = await _chama(
            token, "GET", "/me/businesses", "listar os negócios", params={"fields": "id,name"}
        )
    except CredencialInvalida:
        return []
    encontradas: list[dict[str, str]] = []
    for negocio in negocios.get("data", []):
        if not isinstance(negocio, dict) or not negocio.get("id"):
            continue
        for borda in ("owned_whatsapp_business_accounts", "client_whatsapp_business_accounts"):
            try:
                corpo = await _chama(
                    token,
                    "GET",
                    f"/{negocio['id']}/{borda}",
                    "listar as contas de WhatsApp",
                    params={"fields": "id,name", "limit": 100},
                )
            except CredencialInvalida:
                continue
            for conta in corpo.get("data", []):
                if isinstance(conta, dict) and conta.get("id"):
                    encontradas.append(
                        {"waba_id": str(conta["id"]), "nome": str(conta.get("name") or "")}
                    )
    return encontradas


async def _nome_da_conta(token: str, waba_id: str) -> str:
    try:
        corpo = await _chama(
            token, "GET", f"/{waba_id}", "ler a conta", params={"fields": "name"}
        )
    except CredencialInvalida:
        return ""
    return str(corpo.get("name") or "")


async def numeros_da_conta(token: str, waba_id: str) -> list[dict[str, Any]]:
    """Números da conta de WhatsApp Business, para o operador escolher qual é o do agente."""
    corpo = await _chama(
        token,
        "GET",
        f"/{waba_id}/phone_numbers",
        "listar os números da conta",
        params={"fields": "id,display_phone_number,verified_name,quality_rating", "limit": 100},
    )
    return [
        {
            "phone_number_id": str(item.get("id")),
            "numero": str(item.get("display_phone_number") or ""),
            "nome": str(item.get("verified_name") or ""),
        }
        for item in corpo.get("data", [])
        if isinstance(item, dict) and item.get("id")
    ]


async def numero(token: str, phone_number_id: str) -> dict[str, Any]:
    corpo = await _chama(
        token,
        "GET",
        f"/{phone_number_id}",
        "ler o número",
        params={"fields": "display_phone_number,verified_name"},
    )
    return {
        "numero": str(corpo.get("display_phone_number") or ""),
        "nome": str(corpo.get("verified_name") or ""),
    }


async def templates(token: str, waba_id: str) -> list[dict[str, Any]]:
    """Templates da conta, com idioma, situação e quantos parâmetros o corpo pede.

    O aviso de handoff precisa de um template aprovado com três parâmetros: contato, resumo e
    código. O setup usa a contagem para não deixar escolher um template que não serve.
    """
    corpo = await _chama(
        token,
        "GET",
        f"/{waba_id}/message_templates",
        "listar os templates",
        params={"fields": "name,language,status,category,components", "limit": LIMITE_TEMPLATES},
    )
    encontrados = []
    for item in corpo.get("data", []):
        if not isinstance(item, dict) or not item.get("name"):
            continue
        encontrados.append(
            {
                "nome": str(item["name"]),
                "idioma": str(item.get("language") or ""),
                "situacao": str(item.get("status") or ""),
                "categoria": str(item.get("category") or ""),
                "parametros": _parametros_do_corpo(item.get("components")),
            }
        )
    return encontrados


def _parametros_do_corpo(componentes: Any) -> int:
    """Quantos `{{n}}` o corpo do template tem. Só o corpo recebe os dados do aviso."""
    if not isinstance(componentes, list):
        return 0
    for componente in componentes:
        if isinstance(componente, dict) and str(componente.get("type", "")).upper() == "BODY":
            texto = str(componente.get("text") or "")
            numeros = {t for t in range(1, 10) if f"{{{{{t}}}}}" in texto}
            return len(numeros)
    return 0


# ── Webhook ────────────────────────────────────────────────────────────────


async def liga_webhook_do_app(app_id: str, app_secret: str, url: str, verify_token: str) -> None:
    """Liga os webhooks do app no objeto da conta de WhatsApp Business, com o campo `messages`.

    É o alicerce: o endereço apontado no número (override) só recebe se o app estiver assinando o
    campo. A Meta confere a URL na hora, com `hub.challenge`. O token aqui é o do app, montado com
    o id e o segredo, e não o token de acesso do número.
    """
    await _chama(
        f"{app_id}|{app_secret}",
        "POST",
        f"/{app_id}/subscriptions",
        "ligar os webhooks do app",
        params={
            "object": OBJETO_DO_WEBHOOK,
            "callback_url": url,
            "fields": CAMPOS_DO_WEBHOOK,
            "verify_token": verify_token,
        },
    )


async def inscreve_app(token: str, waba_id: str) -> None:
    """Inscreve o app nos webhooks da conta. Sem isso a Meta não entrega nada."""
    await _chama(token, "POST", f"/{waba_id}/subscribed_apps", "inscrever o app nos webhooks")


async def aponta_webhook(token: str, phone_number_id: str, url: str, verify_token: str) -> None:
    """Manda os webhooks daquele número para a URL do agente (webhook override).

    A Meta chama a URL na hora, com `hub.challenge`, antes de aceitar. Por isso cada agente tem o
    próprio endereço e o próprio token: um app da Meta pode atender vários números.
    """
    await _chama(
        token,
        "POST",
        f"/{phone_number_id}",
        "apontar o webhook para este servidor",
        {"webhook_configuration": {"override_callback_uri": url, "verify_token": verify_token}},
    )


async def limpa_webhook(token: str, phone_number_id: str) -> None:
    """Desfaz o override: os webhooks daquele número voltam para a URL do app."""
    await _chama(
        token,
        "POST",
        f"/{phone_number_id}",
        "desfazer o webhook do número",
        {"webhook_configuration": {"override_callback_uri": ""}},
        ignora=CODIGOS_DE_OBJETO_SUMIDO,
    )


# ── Mensagens ──────────────────────────────────────────────────────────────


def _id_da_mensagem(corpo: dict[str, Any]) -> str | None:
    mensagens = corpo.get("messages")
    if isinstance(mensagens, list) and mensagens and isinstance(mensagens[0], dict):
        identificador = mensagens[0].get("id")
        return str(identificador) if identificador else None
    return None


async def envia_texto(token: str, phone_number_id: str, para: str, texto: str) -> str | None:
    corpo = await _chama(
        token,
        "POST",
        f"/{phone_number_id}/messages",
        "enviar a mensagem",
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": para,
            "type": "text",
            "text": {"preview_url": False, "body": texto},
        },
    )
    return _id_da_mensagem(corpo)


async def envia_template(
    token: str,
    phone_number_id: str,
    para: str,
    nome: str,
    idioma: str,
    parametros: list[str],
) -> str | None:
    """Template aprovado: o único jeito de escrever para quem não falou com o número nas últimas 24 h."""
    componentes = (
        [{"type": "body", "parameters": [{"type": "text", "text": p} for p in parametros]}]
        if parametros
        else []
    )
    corpo = await _chama(
        token,
        "POST",
        f"/{phone_number_id}/messages",
        f"enviar o template {nome}",
        {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": para,
            "type": "template",
            "template": {
                "name": nome,
                "language": {"code": idioma},
                "components": componentes,
            },
        },
    )
    return _id_da_mensagem(corpo)


async def digitando(token: str, phone_number_id: str, mensagem_id: str) -> None:
    """Marca a mensagem como lida e liga o digitando, que some ao responder ou em 25 s.

    A Cloud API não tem como desligar: o indicador é preso à mensagem que chegou.
    """
    await _chama(
        token,
        "POST",
        f"/{phone_number_id}/messages",
        "mostrar o digitando",
        {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": mensagem_id,
            "typing_indicator": {"type": "text"},
        },
    )


async def endereco_da_midia(token: str, media_id: str) -> dict[str, Any]:
    """A URL do arquivo vale poucos minutos e só abre com o mesmo token."""
    corpo = await _chama(token, "GET", f"/{media_id}", "ler o arquivo")
    return {
        "url": str(corpo.get("url") or ""),
        "tipo_mime": str(corpo.get("mime_type") or "").split(";")[0].strip().lower(),
        "tamanho": corpo.get("file_size") if isinstance(corpo.get("file_size"), int) else None,
    }
