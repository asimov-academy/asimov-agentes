"""WhatsApp pela WAHA: assinatura, o que o agente lê, handoff por aviso e retomada.

Só a rede da WAHA é substituída (`WahaFalsa` troca as funções de `canais/waha/api.py`): assinatura,
interpretação do webhook, validação do destino e o aviso de handoff são os de verdade.
"""

import json
import uuid
from typing import Any

import httpx
import pytest
from arq import create_pool
from arq.connections import RedisSettings
from pydantic_ai.models.function import FunctionModel
from sqlalchemy import select

from app.canais.waha import api
from app.canais.waha.assinatura import assina
from app.canais.waha.canal import numero_legivel
from app.conversas import turno
from app.conversas.modelos import Conversa, Mensagem
from app.handoff import repo as handoff_repo
from app.handoff import servico as handoff
from app.handoff.modelos import Handoff
from app.plataforma.banco import agora, fabrica_sessao
from app.plataforma.config import config
from testes.conftest import ADMIN, CONEXAO_EXEMPLO
from testes.test_handoff import ModeloQueTransfere

CONTATO = "5511988887777@c.us"
DESTINO_NUMERO = {"tipo": "numero", "telefone": "5511977776666"}
CHAT_DO_DESTINO = "5511977776666@c.us"


class WahaFalsa:
    """No lugar da rede: guarda a sessão e a chave criadas e registra o que seria enviado."""

    def __init__(self) -> None:
        self.sessao = ""
        self.hmac = ""
        self.url_webhook = ""
        self.enviadas: list[tuple[str, str]] = []
        self.digitando_chamadas: list[bool] = []
        self.lidas: list[str] = []
        self.desconectadas: list[str] = []

    def instala(self, monkeypatch: pytest.MonkeyPatch) -> "WahaFalsa":
        async def cria_sessao(nome: str, url_webhook: str, chave_hmac: str) -> None:
            self.sessao, self.url_webhook, self.hmac = nome, url_webhook, chave_hmac

        async def envia_texto(sessao: str, chat_id: str, texto: str) -> str:
            self.enviadas.append((chat_id, texto))
            return f"waha-{len(self.enviadas)}"

        async def digitando(sessao: str, chat_id: str, ligado: bool) -> None:
            self.digitando_chamadas.append(ligado)

        async def marca_lida(sessao: str, chat_id: str) -> None:
            self.lidas.append(chat_id)

        async def sai_do_whatsapp(nome: str) -> None:
            self.desconectadas.append(nome)

        async def apaga_sessao(nome: str) -> None:
            return None

        for nome, funcao in (
            ("cria_sessao", cria_sessao),
            ("envia_texto", envia_texto),
            ("digitando", digitando),
            ("marca_lida", marca_lida),
            ("sai_do_whatsapp", sai_do_whatsapp),
            ("apaga_sessao", apaga_sessao),
        ):
            monkeypatch.setattr(api, nome, funcao)
        return self


@pytest.fixture
def waha(monkeypatch: pytest.MonkeyPatch) -> WahaFalsa:
    return WahaFalsa().instala(monkeypatch)


@pytest.fixture(autouse=True)
def sem_espera(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(turno, "tempos_de_digitacao", lambda textos, *a, **k: [0] * len(textos))


@pytest.fixture
async def redis() -> Any:
    pool = await create_pool(RedisSettings.from_dsn(config().redis_url))
    await pool.flushdb()
    yield pool
    await pool.aclose()


async def cria_waha(
    http: httpx.AsyncClient, nome: str = "Ana", cliente: str = "Loja Exemplo", **extra: Any
) -> dict[str, Any]:
    conta = (await http.post("/admin/clientes", json={"nome": cliente}, headers=ADMIN)).json()
    corpo = {"nome": nome, "canal": "waha", "handoff_destino": DESTINO_NUMERO, **extra}
    resp = await http.post(f"/admin/clientes/{conta['id']}/agentes", json=corpo, headers=ADMIN)
    assert resp.status_code == 201, resp.text
    agente = resp.json()
    agente["token"] = agente["url_webhook"].rsplit("/", 1)[1]
    return agente


def payload_waha(
    texto: str = "oi",
    de: str = CONTATO,
    id_mensagem: str = "false_5511988887777@c.us_AAA",
    minha: bool = False,
    midia: dict[str, Any] | None = None,
    evento: str = "message",
) -> dict[str, Any]:
    mensagem: dict[str, Any] = {
        "id": id_mensagem,
        "from": de,
        "fromMe": minha,
        "body": texto,
        "hasMedia": midia is not None,
        "_data": {"notifyName": "Maria"},
    }
    if midia is not None:
        mensagem["media"] = midia
    return {"event": evento, "payload": mensagem}


async def manda(
    http: httpx.AsyncClient,
    agente: dict[str, Any],
    waha: WahaFalsa,
    payload: dict[str, Any] | None = None,
    chave: str | None = None,
    assinar: bool = True,
    sessao: str | None = None,
) -> httpx.Response:
    corpo_json = {**(payload or payload_waha()), "session": sessao or waha.sessao}
    corpo = json.dumps(corpo_json).encode()
    cabecalhos = {"Content-Type": "application/json"}
    if assinar:
        cabecalhos["X-Webhook-Hmac"] = assina(chave or waha.hmac, corpo)
        cabecalhos["X-Webhook-Hmac-Algorithm"] = "sha512"
    return await http.post(f"/webhook/waha/{agente['token']}", content=corpo, headers=cabecalhos)


async def roda_turno(fila: Any, redis: Any) -> str:
    _, cliente_id, conversa_id, token = fila.jobs[-1]
    await redis.set(f"buffer:{conversa_id}", token)
    return await turno.processar_turno({"redis": redis}, cliente_id, conversa_id, token)


async def transfere(http: httpx.AsyncClient, fila: Any, redis: Any, waha: WahaFalsa, agente: dict[str, Any]) -> str:
    """Contato pede humano e o turno transfere. Devolve o código do handoff."""
    await manda(http, agente, waha, payload_waha("quero falar com uma pessoa"))
    assert await roda_turno(fila, redis) == "transferido"
    async with fabrica_sessao()() as s:
        return (await s.scalars(select(Handoff))).one().codigo


# ── Conexão ────────────────────────────────────────────────────────────────


async def test_webhook_do_agente_waha_e_interno_e_a_chave_nao_sai_na_api(http, waha) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    assert agente["url_webhook"] == f"http://api:8000/webhook/waha/{agente['token']}"
    assert waha.url_webhook == agente["url_webhook"]
    assert agente["credenciais"]["sessao"] == waha.sessao
    assert waha.hmac and waha.hmac not in json.dumps(agente)


async def test_numero_do_handoff_vira_chat_id_e_numero_invalido_e_recusado(http, waha) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http, handoff_destino={"tipo": "numero", "telefone": "+55 (11) 97777-6666"})
    assert agente["handoff_destino"]["chat_id"] == CHAT_DO_DESTINO

    conta = (await http.post("/admin/clientes", json={"nome": "Outra"}, headers=ADMIN)).json()
    resp = await http.post(
        f"/admin/clientes/{conta['id']}/agentes",
        json={"nome": "Bia", "canal": "waha", "handoff_destino": {"tipo": "numero", "telefone": "123"}},
        headers=ADMIN,
    )
    assert resp.status_code == 422 and "número" in resp.json()["detail"]


async def test_remover_agente_desconecta_o_numero(http, waha) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    resp = await http.request(
        "DELETE",
        f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}",
        json={"confirmacao": "Ana"},
        headers=ADMIN,
    )

    assert resp.status_code == 200 and resp.json()["canal_desconectado"] is True
    assert waha.desconectadas == [waha.sessao]


async def test_retomada_por_tempo_nao_vale_no_chatwoot(http, canal) -> None:  # type: ignore[no-untyped-def]
    conta = (await http.post("/admin/clientes", json={"nome": "Loja Exemplo"}, headers=ADMIN)).json()

    resp = await http.post(
        f"/admin/clientes/{conta['id']}/agentes",
        json={"nome": "Ana", "canal": "chatwoot", "conexao": CONEXAO_EXEMPLO, "retomada_automatica_horas": 3},
        headers=ADMIN,
    )

    assert resp.status_code == 422 and "retomada por tempo" in resp.json()["detail"]


# ── Webhook ────────────────────────────────────────────────────────────────


async def test_assinatura_invalida_recusa_com_401(http, fila, waha) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    assert (await manda(http, agente, waha, chave="outra")).status_code == 401
    assert (await manda(http, agente, waha, assinar=False)).status_code == 401
    assert fila.jobs == []


async def test_mensagem_do_contato_agenda_turno_e_guarda_o_contato(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    assert (await manda(http, agente, waha, payload_waha("bom dia"))).status_code == 200

    assert len(fila.jobs) == 1
    async with sessao() as s:
        conversa = (await s.scalars(select(Conversa))).one()
        mensagem = (await s.scalars(select(Mensagem))).one()
    assert conversa.id_externo == CONTATO and conversa.canal == "waha"
    assert mensagem.texto == "bom dia"


async def test_propria_mensagem_grupo_e_evento_de_sessao_sao_ignorados(http, fila, waha) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    assert (await manda(http, agente, waha, payload_waha(minha=True))).status_code == 200
    assert (await manda(http, agente, waha, payload_waha(de="12345@g.us"))).status_code == 200
    assert (await manda(http, agente, waha, payload_waha(evento="session.status"))).status_code == 200

    assert fila.jobs == []


async def test_mensagem_de_outra_sessao_e_ignorada(http, fila, waha) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    resp = await manda(http, agente, waha, sessao="sessao-de-outro-agente")

    assert resp.status_code == 200 and fila.jobs == []


async def test_mensagem_repetida_nao_vira_dois_turnos(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    await manda(http, agente, waha, payload_waha("oi"))
    await manda(http, agente, waha, payload_waha("oi"))

    assert len(fila.jobs) == 1
    async with sessao() as s:
        assert len(list(await s.scalars(select(Mensagem)))) == 1


async def test_audio_vira_anexo_para_o_turno_ler(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)
    midia = {
        "url": "http://waha:3000/api/files/audio.ogg",
        "mimetype": "audio/ogg; codecs=opus",
        "filename": "audio.ogg",
    }

    await manda(http, agente, waha, payload_waha("", midia=midia))

    async with sessao() as s:
        mensagem = (await s.scalars(select(Mensagem))).one()
    assert mensagem.tipo == "audio"
    assert mensagem.anexo["referencia"] == midia["url"] and mensagem.anexo["tipo_mime"] == "audio/ogg"


async def test_conversa_de_uma_empresa_nao_aparece_na_outra(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    primeiro = await cria_waha(http, nome="Ana", cliente="Loja Exemplo")
    sessao_do_primeiro = waha.sessao
    hmac_do_primeiro = waha.hmac
    segundo = await cria_waha(http, nome="Bia", cliente="Outra Loja")

    await manda(http, primeiro, waha, chave=hmac_do_primeiro, sessao=sessao_do_primeiro)
    await manda(http, segundo, waha, payload_waha(id_mensagem="false_outra_BBB"))

    async with sessao() as s:
        conversas = list(await s.scalars(select(Conversa)))
    assert len({c.cliente_id for c in conversas}) == 2
    assert {c.agente_id for c in conversas} == {uuid.UUID(primeiro["id"]), uuid.UUID(segundo["id"])}


# ── Handoff ────────────────────────────────────────────────────────────────


async def test_handoff_avisa_o_destino_com_codigo_e_cala_o_agente(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    codigo = await transfere(http, fila, redis, waha, agente)

    async with sessao() as s:
        conversa = (await s.scalars(select(Conversa))).one()
    assert conversa.status == "humano"
    avisos = [texto for chat, texto in waha.enviadas if chat == CHAT_DO_DESTINO]
    assert avisos and f"/retomar {codigo}" in avisos[0] and "+55 11 98888-7777" in avisos[0]

    # Com a conversa em handoff, a mensagem nova é gravada mas o agente não fala.
    await manda(http, agente, waha, payload_waha("alô?", id_mensagem="false_x_CCC"))
    assert await roda_turno(fila, redis) == "humano_conduz"


async def test_retomar_do_destino_devolve_a_conversa_ao_agente(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)
    codigo = await transfere(http, fila, redis, waha, agente)

    resp = await manda(
        http, agente, waha, payload_waha(f"/retomar {codigo}", de=CHAT_DO_DESTINO, id_mensagem="false_destino_DDD")
    )

    assert resp.status_code == 200
    async with sessao() as s:
        fechado = (await s.scalars(select(Handoff))).one()
        conversa = (await s.scalars(select(Conversa).where(Conversa.id_externo == CONTATO))).one()
    assert fechado.retomado_em is not None and fechado.retomado_por == "comando"
    assert conversa.status == "agente"
    assert any("voltou a atender" in texto for _, texto in waha.enviadas)


async def test_retomar_de_outro_numero_vira_conversa_comum(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)
    codigo = await transfere(http, fila, redis, waha, agente)

    await manda(
        http, agente, waha, payload_waha(f"/retomar {codigo}", de="5511900000000@c.us", id_mensagem="false_z_EEE")
    )

    async with sessao() as s:
        aberto = (await s.scalars(select(Handoff))).one()
        conversas = {c.id_externo for c in await s.scalars(select(Conversa))}
    assert aberto.retomado_em is None
    assert "5511900000000@c.us" in conversas


async def test_codigo_que_nao_existe_avisa_quem_mandou(http, fila, waha) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    resp = await manda(http, agente, waha, payload_waha("/retomar ZZZZZZ", de=CHAT_DO_DESTINO))

    assert resp.status_code == 200
    assert any("Não achei conversa" in texto for _, texto in waha.enviadas)


async def test_retomada_automatica_devolve_no_horario_e_avisa(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http, retomada_automatica_horas=2)
    await transfere(http, fila, redis, waha, agente)

    async with fabrica_sessao()() as s:
        aberto = (await s.scalars(select(Handoff))).one()
        assert aberto.retomar_em is not None
        assert await handoff.retomada_automatica(s) == 0, "o prazo ainda não venceu"
        aberto.retomar_em = agora()
        await s.commit()

        assert await handoff.retomada_automatica(s) == 1
        assert await handoff_repo.aberto(s, aberto.cliente_id, aberto.conversa_id) is None
        conversa = (await s.scalars(select(Conversa).where(Conversa.id_externo == CONTATO))).one()
    assert conversa.status == "agente"
    assert any("voltou a atender" in texto for _, texto in waha.enviadas)


@pytest.fixture
def modelo_transfere(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(ModeloQueTransfere()))


def test_numero_legivel() -> None:
    assert numero_legivel("5511988887777@c.us") == "+55 11 98888-7777"
    assert numero_legivel("551188887777@c.us") == "+55 11 8888-7777"
    assert numero_legivel("12132132130@c.us") == "+12132132130"
    assert numero_legivel("12345-abc@g.us") == "12345-abc@g.us"
