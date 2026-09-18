"""WhatsApp oficial (Cloud API): verificação, assinatura, o que o agente lê e handoff por aviso.

Só a rede da Meta é substituída (`MetaFalsa` troca as funções de `canais/whatsapp/api.py`):
verificação do endereço, assinatura, interpretação do webhook, validação do destino e a escolha
entre texto livre e template são as de verdade.
"""

import json
from typing import Any

import httpx
import pytest
from arq import create_pool
from arq.connections import RedisSettings
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select

from app.canais.whatsapp import api
from app.canais.whatsapp.assinatura import assina
from app.consumo.modelos import Falha
from app.conversas import turno
from app.conversas.modelos import Contato, Conversa, Mensagem
from app.handoff.modelos import Handoff
from app.plataforma.banco import agora, fabrica_sessao
from app.plataforma.config import config
from testes.conftest import ADMIN
from testes.test_handoff import ModeloQueTransfere

CONTATO = "5511988887777"
DESTINO = "5511977776666"
NUMERO_ID = "1099"
WABA = "2200"
TOKEN_META = "EAAtoken-permanente"
APP_SECRET = "segredo-do-app-da-meta"
TEMPLATE = {"nome": "aviso_handoff", "idioma": "pt_BR"}
CONEXAO = {
    "waba_id": WABA,
    "phone_number_id": NUMERO_ID,
    "access_token": TOKEN_META,
    "app_secret": APP_SECRET,
}


class MetaFalsa:
    """No lugar da rede: guarda o webhook apontado e registra o que seria enviado."""

    def __init__(self) -> None:
        self.url_webhook = ""
        self.verify_token = ""
        self.inscritos: list[str] = []
        self.limpos: list[str] = []
        self.textos: list[tuple[str, str]] = []
        self.templates: list[tuple[str, str, str, list[str]]] = []
        self.digitando: list[tuple[str, str]] = []
        self.arquivos: dict[str, tuple[bytes, str]] = {}
        self.fora_da_janela: set[str] = set()

    def instala(self, monkeypatch: pytest.MonkeyPatch) -> "MetaFalsa":
        async def numero(token: str, phone_number_id: str) -> dict[str, Any]:
            assert token == TOKEN_META
            return {"numero": "+55 11 3333-4444", "nome": "Loja Exemplo"}

        async def inscreve_app(token: str, waba_id: str) -> None:
            self.inscritos.append(waba_id)

        async def aponta_webhook(token: str, phone_number_id: str, url: str, verify: str) -> None:
            self.url_webhook, self.verify_token = url, verify

        async def limpa_webhook(token: str, phone_number_id: str) -> None:
            self.limpos.append(phone_number_id)

        async def envia_texto(token: str, phone_number_id: str, para: str, texto: str) -> str:
            if para in self.fora_da_janela:
                raise api.ForaDaJanela("mais de 24 horas desde a última mensagem")
            self.textos.append((para, texto))
            return f"wamid.saida{len(self.textos)}"

        async def envia_template(
            token: str, phone_number_id: str, para: str, nome: str, idioma: str, parametros: list[str]
        ) -> str:
            self.templates.append((para, nome, idioma, parametros))
            return f"wamid.template{len(self.templates)}"

        async def digitando(token: str, phone_number_id: str, mensagem_id: str) -> None:
            self.digitando.append((phone_number_id, mensagem_id))

        async def endereco_da_midia(token: str, media_id: str) -> dict[str, Any]:
            conteudo, mime = self.arquivos[media_id]
            return {"url": f"https://midia.teste/{media_id}", "tipo_mime": mime, "tamanho": len(conteudo)}

        for nome, funcao in (
            ("numero", numero),
            ("inscreve_app", inscreve_app),
            ("aponta_webhook", aponta_webhook),
            ("limpa_webhook", limpa_webhook),
            ("envia_texto", envia_texto),
            ("envia_template", envia_template),
            ("digitando", digitando),
            ("endereco_da_midia", endereco_da_midia),
        ):
            monkeypatch.setattr(api, nome, funcao)
        return self


@pytest.fixture
def meta(monkeypatch: pytest.MonkeyPatch) -> MetaFalsa:
    return MetaFalsa().instala(monkeypatch)


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(turno, "tempos_de_digitacao", lambda textos, *a, **k: [0] * len(textos))


@pytest.fixture
def modelo_transfere(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(ModeloQueTransfere()))


@pytest.fixture
async def redis() -> Any:
    pool = await create_pool(RedisSettings.from_dsn(config().redis_url))
    await pool.flushdb()
    yield pool
    await pool.aclose()


async def cria_agente(
    http: httpx.AsyncClient, nome: str = "Ana", cliente: str = "Loja Exemplo", **extra: Any
) -> dict[str, Any]:
    conta = (await http.post("/admin/clientes", json={"nome": cliente}, headers=ADMIN)).json()
    corpo = {
        "nome": nome,
        "canal": "whatsapp",
        "conexao": CONEXAO,
        "handoff_destino": {"tipo": "numero", "telefone": DESTINO, "template": TEMPLATE},
        **extra,
    }
    resp = await http.post(f"/admin/clientes/{conta['id']}/agentes", json=corpo, headers=ADMIN)
    assert resp.status_code == 201, resp.text
    agente = resp.json()
    agente["token"] = agente["url_webhook"].rsplit("/", 1)[1]
    return agente


def payload(
    texto: str | None = "oi",
    de: str = CONTATO,
    id_mensagem: str = "wamid.AAA",
    tipo: str = "text",
    midia: dict[str, Any] | None = None,
    reacao: str | None = None,
    numero_id: str = NUMERO_ID,
    statuses: bool = False,
) -> dict[str, Any]:
    valor: dict[str, Any] = {
        "messaging_product": "whatsapp",
        "metadata": {"display_phone_number": "551133334444", "phone_number_id": numero_id},
    }
    if statuses:
        valor["statuses"] = [{"id": "wamid.saida1", "status": "delivered"}]
    else:
        mensagem: dict[str, Any] = {"from": de, "id": id_mensagem, "timestamp": "1770000000", "type": tipo}
        if reacao is not None:
            mensagem["type"] = "reaction"
            mensagem["reaction"] = {"message_id": "wamid.aviso", "emoji": reacao}
        elif midia is not None:
            mensagem[tipo] = midia
        else:
            mensagem["text"] = {"body": texto}
        valor["contacts"] = [{"profile": {"name": "Maria"}, "wa_id": de}]
        valor["messages"] = [mensagem]
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": WABA, "changes": [{"field": "messages", "value": valor}]}],
    }


async def manda(
    http: httpx.AsyncClient,
    agente: dict[str, Any],
    corpo_json: dict[str, Any] | None = None,
    assinar: bool = True,
    segredo: str = APP_SECRET,
) -> httpx.Response:
    corpo = json.dumps(corpo_json or payload()).encode()
    cabecalhos = {"Content-Type": "application/json"}
    if assinar:
        cabecalhos["X-Hub-Signature-256"] = assina(segredo, corpo)
    return await http.post(f"/webhook/whatsapp/{agente['token']}", content=corpo, headers=cabecalhos)


async def roda_turno(fila: Any, redis: Any) -> str:
    _, cliente_id, conversa_id, token = [j for j in fila.jobs if j[0] == "processar_turno"][-1]
    await redis.set(f"buffer:{conversa_id}", token)
    return await turno.processar_turno({"redis": redis}, cliente_id, conversa_id, token)


async def transfere(http: httpx.AsyncClient, fila: Any, redis: Any, agente: dict[str, Any]) -> str:
    await manda(http, agente, payload("quero falar com uma pessoa"))
    assert await roda_turno(fila, redis) == "transferido"
    async with fabrica_sessao()() as s:
        return (await s.scalars(select(Handoff))).one().codigo


# ── Conexão e verificação ──────────────────────────────────────────────────


async def test_conectar_aponta_o_webhook_do_numero_e_esconde_o_token(http, meta) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http)

    assert agente["url_webhook"] == f"https://bot.teste.local/webhook/whatsapp/{agente['token']}"
    assert meta.url_webhook == agente["url_webhook"]
    # O token da URL é o mesmo que a Meta devolve na verificação: não há segundo segredo a guardar.
    assert meta.verify_token == agente["token"]
    assert meta.inscritos == [WABA]
    assert TOKEN_META not in json.dumps(agente) and APP_SECRET not in json.dumps(agente)
    assert agente["credenciais"]["numero"] == "+55 11 3333-4444"


async def test_verificacao_da_meta_devolve_o_desafio_e_recusa_token_errado(http, meta) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http)
    caminho = f"/webhook/whatsapp/{agente['token']}"

    certo = await http.get(
        caminho,
        params={"hub.mode": "subscribe", "hub.verify_token": agente["token"], "hub.challenge": "1234"},
    )
    errado = await http.get(
        caminho, params={"hub.mode": "subscribe", "hub.verify_token": "outro", "hub.challenge": "1234"}
    )

    assert certo.status_code == 200 and certo.text == "1234"
    assert errado.status_code == 404


async def test_verificacao_nao_vale_nos_outros_canais(http) -> None:  # type: ignore[no-untyped-def]
    resp = await http.get(
        "/webhook/chatwoot/qualquer",
        params={"hub.mode": "subscribe", "hub.verify_token": "qualquer", "hub.challenge": "1234"},
    )
    assert resp.status_code == 404


async def test_destino_sem_numero_valido_e_recusado(http, meta) -> None:  # type: ignore[no-untyped-def]
    conta = (await http.post("/admin/clientes", json={"nome": "Outra"}, headers=ADMIN)).json()

    resp = await http.post(
        f"/admin/clientes/{conta['id']}/agentes",
        json={
            "nome": "Bia",
            "canal": "whatsapp",
            "conexao": CONEXAO,
            "handoff_destino": {"tipo": "numero", "telefone": "123"},
        },
        headers=ADMIN,
    )

    assert resp.status_code == 422 and "número" in resp.json()["detail"]


async def test_remover_agente_devolve_o_webhook_do_numero(http, meta) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http)

    resp = await http.request(
        "DELETE",
        f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}",
        json={"confirmacao": "Ana"},
        headers=ADMIN,
    )

    assert resp.status_code == 200 and resp.json()["canal_desconectado"] is True
    assert meta.limpos == [NUMERO_ID]


# ── Webhook ────────────────────────────────────────────────────────────────


async def test_assinatura_invalida_recusa_com_401(http, fila, meta) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http)

    sem = await manda(http, agente, assinar=False)
    outra = await manda(http, agente, segredo="segredo-errado")

    assert sem.status_code == 401 and outra.status_code == 401
    assert fila.jobs == []
    async with fabrica_sessao()() as s:
        falhas = (await s.scalars(select(Falha))).all()
    assert [f.tipo for f in falhas] == ["webhook_assinatura_invalida"] * 2


async def test_mensagem_do_contato_vira_conversa_e_resposta(http, fila, meta, redis, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from testes.conftest import resposta_falsa

    monkeypatch.setattr(
        "app.ia.provedores.construir_modelo",
        lambda nome: FunctionModel(lambda h, info: resposta_falsa(info, ["Oi, Maria"])),
    )
    agente = await cria_agente(http)

    assert (await manda(http, agente)).status_code == 200
    assert await roda_turno(fila, redis) == "respondido"

    assert meta.textos == [(CONTATO, "Oi, Maria")]
    # O digitando da Cloud API é preso à mensagem que chegou, e marca a leitura junto.
    assert meta.digitando and meta.digitando[0] == (NUMERO_ID, "wamid.AAA")
    async with fabrica_sessao()() as s:
        conversa = (await s.scalars(select(Conversa))).one()
        contato = await s.get(Contato, conversa.contato_id)
    assert conversa.id_externo == CONTATO and conversa.canal == "whatsapp"
    assert contato.nome == "Maria" and contato.telefone == CONTATO


async def test_recibo_de_entrega_e_numero_de_outro_agente_sao_ignorados(http, fila, meta) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http)

    recibo = await manda(http, agente, payload(statuses=True))
    outro = await manda(http, agente, payload("oi", numero_id="9999"))

    assert recibo.status_code == 200 and outro.status_code == 200
    assert fila.jobs == []
    async with fabrica_sessao()() as s:
        assert (await s.scalars(select(Mensagem))).all() == []


async def test_imagem_chega_como_anexo_com_o_id_da_meta(http, fila, meta) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http)

    resp = await manda(
        http,
        agente,
        payload(tipo="image", midia={"id": "midia-1", "mime_type": "image/jpeg", "caption": "olha isso"}),
    )

    assert resp.status_code == 200
    async with fabrica_sessao()() as s:
        mensagem = (await s.scalars(select(Mensagem))).one()
    assert mensagem.tipo == "imagem" and mensagem.texto == "olha isso"
    assert mensagem.anexo["referencia"] == "midia-1"


async def test_baixar_midia_pega_o_endereco_e_o_arquivo_com_o_mesmo_token(meta, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    from app.canais.base import Anexo
    from app.canais.registro import obter_canal

    meta.arquivos["midia-1"] = (b"conteudo do audio", "audio/ogg")
    pedidos: list[tuple[str, str]] = []

    def transporte(pedido: httpx.Request) -> httpx.Response:
        pedidos.append((str(pedido.url), pedido.headers.get("authorization", "")))
        return httpx.Response(200, content=b"conteudo do audio", headers={"content-type": "audio/ogg"})

    original = httpx.AsyncClient

    def cliente(*args: Any, **kwargs: Any) -> httpx.AsyncClient:
        return original(*args, **{**kwargs, "transport": httpx.MockTransport(transporte)})

    monkeypatch.setattr("app.canais.whatsapp.canal.httpx.AsyncClient", cliente)

    baixado = await obter_canal("whatsapp").baixar_midia(
        CONEXAO, Anexo(tipo="audio", referencia="midia-1"), 1_000_000
    )

    assert baixado.conteudo == b"conteudo do audio" and baixado.tipo_mime == "audio/ogg"
    assert pedidos == [("https://midia.teste/midia-1", f"Bearer {TOKEN_META}")]


# ── Handoff ────────────────────────────────────────────────────────────────


async def test_handoff_avisa_o_destino_e_cala_o_agente(http, fila, meta, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http)

    codigo = await transfere(http, fila, redis, agente)

    async with sessao() as s:
        conversa = (await s.scalars(select(Conversa))).one()
    assert conversa.status == "humano"
    avisos = [texto for para, texto in meta.textos if para == DESTINO]
    assert avisos and f"/retomar {codigo}" in avisos[0] and "+55 11 98888-7777" in avisos[0]

    await manda(http, agente, payload("alô?", id_mensagem="wamid.CCC"))
    assert await roda_turno(fila, redis) == "humano_conduz"


async def test_fora_da_janela_de_24_horas_o_aviso_sai_por_template(http, fila, meta, redis, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http)
    meta.fora_da_janela.add(DESTINO)

    codigo = await transfere(http, fila, redis, agente)

    assert [para for para, _ in meta.textos if para == DESTINO] == []
    para, nome, idioma, parametros = meta.templates[0]
    assert (para, nome, idioma) == (DESTINO, "aviso_handoff", "pt_BR")
    assert parametros[0].startswith("Maria") and parametros[2] == codigo
    # Parâmetro de template não aceita quebra de linha.
    assert all("\n" not in p for p in parametros)


async def test_sem_template_e_fora_da_janela_a_falha_diz_o_que_fazer(http, fila, meta, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http, handoff_destino={"tipo": "numero", "telefone": DESTINO})
    meta.fora_da_janela.add(DESTINO)

    await transfere(http, fila, redis, agente)

    async with sessao() as s:
        falha = (await s.scalars(select(Falha).where(Falha.tipo == "handoff_incompleto"))).one()
    assert "template" in json.dumps(falha.detalhe)


async def test_retomar_do_destino_devolve_e_de_outro_numero_vira_conversa(http, fila, meta, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http)
    codigo = await transfere(http, fila, redis, agente)

    de_fora = await manda(http, agente, payload(f"/retomar {codigo}", de="5511911112222", id_mensagem="wamid.DDD"))
    do_destino = await manda(http, agente, payload(f"/retomar {codigo}", de=DESTINO, id_mensagem="wamid.EEE"))

    assert de_fora.status_code == 200 and do_destino.status_code == 200
    async with sessao() as s:
        conversas = {c.id_externo: c.status for c in (await s.scalars(select(Conversa))).all()}
    assert conversas[CONTATO] == "agente"
    # O mesmo texto de outro número é conversa comum: virou uma conversa nova.
    assert conversas["5511911112222"] == "agente"
    assert any("voltou a atender" in texto for para, texto in meta.textos if para == DESTINO)


async def test_joinha_do_destino_devolve_e_do_contato_nao(http, fila, meta, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http)
    await transfere(http, fila, redis, agente)

    do_contato = await manda(http, agente, payload(reacao="\U0001f44d", de=CONTATO, id_mensagem="wamid.FFF"))
    async with sessao() as s:
        assert (await s.scalars(select(Conversa).where(Conversa.id_externo == CONTATO))).one().status == "humano"

    do_destino = await manda(http, agente, payload(reacao="\U0001f44d", de=DESTINO, id_mensagem="wamid.GGG"))

    assert do_contato.status_code == 200 and do_destino.status_code == 200
    async with sessao() as s:
        assert (await s.scalars(select(Conversa).where(Conversa.id_externo == CONTATO))).one().status == "agente"


async def test_retomada_automatica_devolve_no_horario_e_avisa(http, fila, meta, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    from datetime import timedelta

    from app.handoff import servico as handoff

    agente = await cria_agente(http, retomada_automatica_horas=4)
    await transfere(http, fila, redis, agente)

    async with sessao() as s:
        aberto = (await s.scalars(select(Handoff))).one()
        aberto.retomar_em = agora() - timedelta(minutes=1)
        await s.commit()
    async with sessao() as s:
        assert await handoff.retomada_automatica(s) == 1

    async with sessao() as s:
        assert (await s.scalars(select(Conversa))).one().status == "agente"
    assert any("voltou a atender" in texto for para, texto in meta.textos if para == DESTINO)


async def test_contato_fora_da_lista_nao_vira_conversa(http, fila, meta) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_agente(http, contatos_permitidos=["5511900001111"])

    resp = await manda(http, agente, payload("oi", de=CONTATO))

    assert resp.status_code == 200 and fila.jobs == []
    async with fabrica_sessao()() as s:
        falha = (await s.scalars(select(Falha))).one()
    assert falha.tipo == "contato_fora_da_lista"


def test_rotulo_da_conversa_mostra_o_telefone() -> None:
    from app.canais.registro import obter_canal

    canal = obter_canal("whatsapp")
    assert canal.rotulo_da_conversa("5511988887777") == "+55 11 98888-7777"
    assert canal.rotulo_da_conversa("5511988887777@c.us") == "+55 11 98888-7777"


def test_conta_os_parametros_do_corpo_do_template() -> None:
    componentes = [
        {"type": "HEADER", "text": "Atendimento"},
        {"type": "BODY", "text": "Contato: {{1}}\nResumo: {{2}}\nCódigo: {{3}}"},
    ]
    assert api._parametros_do_corpo(componentes) == 3
    assert api._parametros_do_corpo([{"type": "BODY", "text": "sem parâmetro"}]) == 0
