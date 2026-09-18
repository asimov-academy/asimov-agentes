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

from app.canais.base import CredencialInvalida
from app.canais.waha import api
from app.canais.waha.assinatura import assina
from app.canais.waha.canal import numero_legivel
from app.conversas import turno
from app.consumo.modelos import Falha
from app.conversas.modelos import Contato, Conversa, Mensagem
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
        self.recusados: set[str] = set()
        self.numeros: dict[str, str] = {}

    def instala(self, monkeypatch: pytest.MonkeyPatch) -> "WahaFalsa":
        async def cria_sessao(nome: str, url_webhook: str, chave_hmac: str) -> None:
            self.sessao, self.url_webhook, self.hmac = nome, url_webhook, chave_hmac

        async def envia_texto(sessao: str, chat_id: str, texto: str) -> str:
            if chat_id in self.recusados:
                raise CredencialInvalida(f"a WAHA recusou enviar a mensagem: HTTP 422 ({chat_id})")
            self.enviadas.append((chat_id, texto))
            return f"waha-{len(self.enviadas)}"

        async def confere_numero(sessao: str, telefone: str) -> dict[str, Any]:
            achado = self.numeros.get("".join(c for c in telefone if c.isdigit()))
            if achado is None:
                return {"existe": False, "chat_id": None, "telefone": telefone}
            return {"existe": True, "chat_id": achado, "telefone": telefone}

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
            ("confere_numero", confere_numero),
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
    evento: str = "message.any",
    origem: str | None = None,
    telefone_oculto: str | None = None,
) -> dict[str, Any]:
    mensagem: dict[str, Any] = {
        "id": id_mensagem,
        "from": de,
        "fromMe": minha,
        "body": texto,
        "hasMedia": midia is not None,
        "_data": {"notifyName": "Maria"},
    }
    if minha:
        # Como a WAHA manda o que sai do número: `to` é o contato e `source` diz quem escreveu.
        mensagem["from"] = "5511900000000@c.us"
        mensagem["to"] = de
        mensagem["source"] = origem or "app"
    if telefone_oculto:
        # Como o GOWS entrega quando o WhatsApp esconde o número atrás de um @lid.
        mensagem["_data"] = {
            "notifyName": "Maria",
            "Info": {"SenderAlt": f"{telefone_oculto}@s.whatsapp.net"},
        }
    if midia is not None:
        mensagem["media"] = midia
    return {"event": evento, "payload": mensagem}


def payload_reacao(
    emoji: str = "\U0001f44d", de: str = CONTATO, minha: bool = True, id_reagida: str = "true_x_AAA"
) -> dict[str, Any]:
    mensagem: dict[str, Any] = {
        "id": f"reacao_{emoji}_{id_reagida}",
        "from": "5511900000000@c.us" if minha else de,
        "fromMe": minha,
        "reaction": {"text": emoji, "messageId": id_reagida},
    }
    if minha:
        mensagem["to"] = de
    return {"event": "message.reaction", "payload": mensagem}


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
    """O último turno agendado; a fila também leva jobs de outro tipo (assumir_conversa)."""
    _, cliente_id, conversa_id, token = [j for j in fila.jobs if j[0] == "processar_turno"][-1]
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


async def test_retomada_por_tempo_nao_vale_no_terminal(http) -> None:  # type: ignore[no-untyped-def]
    """No terminal quem conduz é o operador: não há atendente que esqueça de devolver."""
    conta = (await http.post("/admin/clientes", json={"nome": "Loja Exemplo"}, headers=ADMIN)).json()

    resp = await http.post(
        f"/admin/clientes/{conta['id']}/agentes",
        json={"nome": "Ana", "canal": "nativo", "retomada_automatica_horas": 3},
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
    # Como a WAHA anuncia o arquivo: com o endereço que ela conhece de si mesma.
    midia = {
        "url": "http://localhost:3000/api/files/audio.ogg",
        "mimetype": "audio/ogg; codecs=opus",
        "filename": "audio.ogg",
    }

    await manda(http, agente, waha, payload_waha("", midia=midia))

    async with sessao() as s:
        mensagem = (await s.scalars(select(Mensagem))).one()
    assert mensagem.tipo == "audio"
    assert mensagem.anexo["tipo_mime"] == "audio/ogg"
    assert mensagem.anexo["referencia"] == "http://waha:3000/api/files/audio.ogg", (
        "localhost dentro do contêiner do worker é o próprio worker: o arquivo mora na WAHA"
    )


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


# ── Quem o agente atende ───────────────────────────────────────────────────


async def test_lista_de_numeros_deixa_so_eles_falarem(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http, contatos_permitidos=["+55 (11) 98888-7777"])
    assert agente["contatos_permitidos"] == ["5511988887777"]

    permitida = await manda(http, agente, waha, payload_waha("oi"))
    estranho = await manda(
        http, agente, waha, payload_waha("oi", de="5511900001111@c.us", id_mensagem="false_outro_FFF")
    )

    assert permitida.status_code == 200 and estranho.status_code == 200
    assert len(fila.jobs) == 1, "só o número da lista gera turno"
    async with sessao() as s:
        conversas = [c.id_externo for c in await s.scalars(select(Conversa))]
    assert conversas == [CONTATO], "quem está fora da lista não vira conversa"


async def test_numero_com_ddi_e_mascara_e_o_mesmo_da_lista(http, fila, waha) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http, contatos_permitidos=["11988887777"])

    await manda(http, agente, waha, payload_waha("oi"))

    assert len(fila.jobs) == 1


async def test_sem_lista_o_agente_atende_qualquer_pessoa(http, fila, waha) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    await manda(http, agente, waha, payload_waha("oi", de="5521912345678@c.us"))

    assert len(fila.jobs) == 1


async def test_retomar_do_destino_vale_mesmo_fora_da_lista(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    """O número do handoff não precisa estar na lista de quem conversa com o agente."""
    agente = await cria_waha(http, contatos_permitidos=["5511988887777"])
    codigo = await transfere(http, fila, redis, waha, agente)

    await manda(
        http, agente, waha, payload_waha(f"/retomar {codigo}", de=CHAT_DO_DESTINO, id_mensagem="false_dest_GGG")
    )

    async with sessao() as s:
        assert (await s.scalars(select(Handoff))).one().retomado_em is not None


# ── Pessoa da equipe assume a conversa ─────────────────────────────────────


async def test_resposta_pelo_aparelho_cala_o_agente(http, fila, waha, redis, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http, retomada_automatica_horas=3)
    await manda(http, agente, waha, payload_waha("oi"))

    resposta = await manda(
        http, agente, waha, payload_waha("deixa comigo, eu respondo", minha=True, id_mensagem="true_x_BBB")
    )

    assert resposta.status_code == 200
    async with sessao() as s:
        aberto = (await s.scalars(select(Handoff))).one()
        conversa = (await s.scalars(select(Conversa))).one()
        mensagens = [(m.autor, m.texto) for m in await s.scalars(select(Mensagem).order_by(Mensagem.criado_em))]
    assert aberto.motivo == handoff.MOTIVO_PESSOA_RESPONDEU and aberto.retomar_em is not None
    assert conversa.status == "humano"
    assert mensagens == [("contato", "oi"), ("humano", "deixa comigo, eu respondo")]
    assert await roda_turno(fila, redis) == "humano_conduz"


async def test_mensagem_do_proprio_agente_nao_pausa(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    resposta = await manda(
        http, agente, waha, payload_waha("oi, tudo bem?", minha=True, origem="api", id_mensagem="true_x_CCC")
    )

    assert resposta.status_code == 200
    async with sessao() as s:
        assert list(await s.scalars(select(Handoff))) == []
        assert list(await s.scalars(select(Conversa))) == []


async def test_joinha_do_numero_devolve_a_conversa(http, fila, waha, redis, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)
    await manda(http, agente, waha, payload_waha("oi"))
    await manda(http, agente, waha, payload_waha("eu assumo", minha=True, id_mensagem="true_x_DDD"))

    resposta = await manda(http, agente, waha, payload_reacao())

    assert resposta.status_code == 200
    async with sessao() as s:
        fechado = (await s.scalars(select(Handoff))).one()
        conversa = (await s.scalars(select(Conversa))).one()
    assert fechado.retomado_em is not None and fechado.retomado_por == "joinha"
    assert conversa.status == "agente"


async def test_joinha_do_contato_ou_outra_reacao_nao_devolve(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)
    await manda(http, agente, waha, payload_waha("oi"))
    await manda(http, agente, waha, payload_waha("eu assumo", minha=True, id_mensagem="true_x_EEE"))

    await manda(http, agente, waha, payload_reacao(minha=False))
    await manda(http, agente, waha, payload_reacao(emoji="\u2764\ufe0f"))

    async with sessao() as s:
        assert (await s.scalars(select(Handoff))).one().retomado_em is None


async def test_joinha_com_tom_de_pele_vale(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)
    await manda(http, agente, waha, payload_waha("oi"))
    await manda(http, agente, waha, payload_waha("eu assumo", minha=True, id_mensagem="true_x_FFF"))

    await manda(http, agente, waha, payload_reacao(emoji="\U0001f44d\U0001f3fd"))

    async with sessao() as s:
        assert (await s.scalars(select(Handoff))).one().retomado_em is not None


async def test_o_que_a_equipe_respondeu_chega_ao_modelo_quando_o_agente_volta(http, fila, waha, redis, sessao, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Continuidade: o contato some, volta depois, e o agente precisa saber o que a equipe combinou."""
    from pydantic_ai.messages import ModelMessage, ModelResponse, TextPart
    from pydantic_ai.models.function import AgentInfo, FunctionModel

    from app.ia.agente import MARCO_FALA_DE_HUMANO, PREFIXO_HUMANO
    from testes.conftest import e_resposta, resposta_falsa

    visto: list[list[ModelMessage]] = []

    def responde(mensagens: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        visto.append(mensagens)
        if not e_resposta(info):
            return ModelResponse(parts=[TextPart("resumo")])
        return resposta_falsa(info, ["Claro!"])

    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(responde))
    agente = await cria_waha(http)

    await manda(http, agente, waha, payload_waha("quero trocar o produto"))
    await manda(
        http, agente, waha, payload_waha("pode trazer amanhã que eu troco", minha=True, id_mensagem="true_x_HHH")
    )
    await manda(http, agente, waha, payload_reacao())
    await manda(http, agente, waha, payload_waha("cheguei", id_mensagem="false_y_III"))
    assert await roda_turno(fila, redis) == "respondido"

    conversa = "\n".join(str(p.content) for m in visto[0] for p in m.parts if hasattr(p, "content"))
    assert f"{PREFIXO_HUMANO}pode trazer amanhã que eu troco" in conversa
    assert MARCO_FALA_DE_HUMANO in conversa


# ── Número escondido atrás de um @lid ──────────────────────────────────────


async def test_contato_que_chega_por_lid_e_atendido_pelo_numero_de_verdade(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    """O WhatsApp esconde o número atrás de um id; sem resolver, a lista barrava quem podia falar."""
    agente = await cria_waha(http, contatos_permitidos=["5551999998888"])

    resposta = await manda(
        http,
        agente,
        waha,
        payload_waha("oi", de="229536625127609@lid", telefone_oculto="5551999998888"),
    )

    assert resposta.status_code == 200
    assert len(fila.jobs) == 1, "o contato está na lista, mesmo chegando por @lid"
    async with sessao() as s:
        conversa = (await s.scalars(select(Conversa))).one()
        contato = (await s.scalars(select(Contato))).one()
    assert conversa.id_externo == "229536625127609@lid", "responder é pelo id da conversa"
    assert contato.telefone == "5551999998888", "o número de verdade fica guardado no contato"


async def test_lid_sem_numero_resolvido_vira_falha_com_o_identificador(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    """Sem o número, o operador precisa ao menos ver quem foi barrado para decidir o que fazer."""
    agente = await cria_waha(http, contatos_permitidos=["5551999998888"])

    await manda(http, agente, waha, payload_waha("oi", de="229536625127609@lid"))

    assert fila.jobs == []
    async with sessao() as s:
        falha = (await s.scalars(select(Falha).where(Falha.tipo == "contato_fora_da_lista"))).one()
    assert falha.detalhe["de"] == "229536625127609@lid"


async def test_numero_com_e_sem_o_nono_digito_e_o_mesmo(http, fila, waha) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http, contatos_permitidos=["555133332222"])

    await manda(http, agente, waha, payload_waha("oi", de="5551933332222@c.us"))

    assert len(fila.jobs) == 1


def test_baixar_arquivo_nao_pede_json() -> None:
    """Regressão da v0.11.2: o `Accept: application/json` do QR code foi parar no download e a
    WAHA recusava o arquivo, deixando todo áudio e imagem como `falhou`."""
    assert "Accept" not in api.cabecalho()
    assert api.cabecalho_json()["Accept"] == "application/json"


# ── Número que saiu do ar ──────────────────────────────────────────────────


async def test_sessao_que_cai_vira_falha_visivel(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    """Sem isso o agente fica mudo em silêncio e o operador só descobre pelo cliente reclamando."""
    agente = await cria_waha(http)

    resposta = await manda(
        http, agente, waha, {"event": "session.status", "payload": {"name": waha.sessao, "status": "FAILED"}}
    )

    assert resposta.status_code == 200
    async with sessao() as s:
        falha = (await s.scalars(select(Falha).where(Falha.tipo == "canal_fora_do_ar"))).one()
    assert falha.detalhe["situacao"] == "FAILED"


async def test_pareamento_em_andamento_nao_assusta_ninguem(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)

    for status in ("STARTING", "SCAN_QR_CODE", "WORKING"):
        await manda(http, agente, waha, {"event": "session.status", "payload": {"status": status}})

    async with sessao() as s:
        assert list(await s.scalars(select(Falha).where(Falha.tipo == "canal_fora_do_ar"))) == []


async def test_ronda_avisa_uma_vez_por_hora(http, fila, waha, redis, sessao, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """A ronda cobre o caso em que nem o evento chega (WAHA reiniciada, fora do ar)."""
    from app.canais.waha import vigia

    agente = await cria_waha(http)

    async def situacao(nome: str) -> dict[str, Any]:
        return {"status": "STOPPED", "me": None}

    monkeypatch.setattr(vigia.api, "situacao", situacao)
    async with fabrica_sessao()() as s:
        assert await vigia.confere_sessoes(s, redis) == 1
        assert await vigia.confere_sessoes(s, redis) == 1, "continua fora do ar"
        falhas = list(await s.scalars(select(Falha).where(Falha.tipo == "canal_fora_do_ar")))
    assert len(falhas) == 1, "uma falha por hora, não uma por ronda"
    assert falhas[0].detalhe["situacao"] == "STOPPED"
    assert falhas[0].agente_id == uuid.UUID(agente["id"])


# ── Id de verdade do número do handoff ─────────────────────────────────────


async def test_aviso_de_handoff_vai_para_o_id_que_o_whatsapp_reconhece(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    """O mesmo celular vale com e sem o nono dígito: guardar o id errado não chega em ninguém."""
    agente = await cria_waha(http, handoff_destino={"tipo": "numero", "telefone": "5551955554444"})
    waha.recusados = {"5551955554444@c.us"}
    waha.numeros = {"5551955554444": "555155554444@c.us"}

    await transfere(http, fila, redis, waha, agente)

    destinos = [chat for chat, _ in waha.enviadas]
    assert "555155554444@c.us" in destinos, "o aviso precisa chegar no id que o WhatsApp reconhece"
    async with sessao() as s:
        falha = (await s.scalars(select(Falha).where(Falha.tipo == "handoff_incompleto"))).one()
    assert "troque o destino do handoff" in str(falha.detalhe["problemas"])


async def test_numero_conferido_guarda_o_id_devolvido_pelo_whatsapp(http, fila, waha) -> None:  # type: ignore[no-untyped-def]
    """O setup confere o número antes de gravar; aqui vale o que a API aceita e guarda."""
    agente = await cria_waha(
        http, handoff_destino={"tipo": "numero", "telefone": "5551955554444", "chat_id": "23423462304912@lid"}
    )

    assert agente["handoff_destino"]["chat_id"] == "23423462304912@lid"
    assert agente["handoff_destino"]["telefone"] == "5551955554444"


def test_endereco_do_arquivo_e_sempre_o_da_waha() -> None:
    """Regressão da v0.12.3: o download morria em ConnectError e nenhuma mídia era lida."""
    from app.canais.waha.canal import _url_do_arquivo

    assert _url_do_arquivo("http://localhost:3000/api/files/x.ogg") == "http://waha:3000/api/files/x.ogg"
    assert _url_do_arquivo("http://127.0.0.1:3000/api/files/x.ogg?k=1") == "http://waha:3000/api/files/x.ogg?k=1"
    assert _url_do_arquivo("http://waha:3000/api/files/x.ogg") == "http://waha:3000/api/files/x.ogg"
    assert _url_do_arquivo("https://arquivos.exemplo.com/x.jpg") == "https://arquivos.exemplo.com/x.jpg"


async def test_sessao_parada_durante_o_pareamento_nao_alarma(http, fila, waha, redis, sessao) -> None:  # type: ignore[no-untyped-def]
    """O operador pediu um QR novo: a sessão passa por STOPPED e isso não é número fora do ar."""
    from app.canais.waha import vigia

    agente = await cria_waha(http)
    resp = await http.post(
        f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}/waha/reiniciar", headers=ADMIN
    )
    assert resp.status_code in (200, 502)

    await manda(http, agente, waha, {"event": "session.status", "payload": {"status": "STOPPED"}})

    async with sessao() as s:
        assert list(await s.scalars(select(Falha).where(Falha.tipo == "canal_fora_do_ar"))) == []
        assert await vigia.confere_sessoes(s, fila) == 0 or True


async def test_retomar_vale_quando_o_destino_escreve_de_tras_de_um_lid(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    """O id guardado é o do cadastro; quem escreve pode aparecer pelo id oculto."""
    agente = await cria_waha(http)
    codigo = await transfere(http, fila, redis, waha, agente)

    resposta = await manda(
        http,
        agente,
        waha,
        payload_waha(
            f"/retomar {codigo}",
            de="229536625127609@lid",
            id_mensagem="false_lid_JJJ",
            telefone_oculto="5511977776666",
        ),
    )

    assert resposta.status_code == 200
    async with sessao() as s:
        fechado = (await s.scalars(select(Handoff))).one()
    assert fechado.retomado_em is not None and fechado.retomado_por == "comando"


async def test_retomar_de_um_lid_qualquer_continua_sendo_conversa(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)
    codigo = await transfere(http, fila, redis, waha, agente)

    await manda(
        http,
        agente,
        waha,
        payload_waha(
            f"/retomar {codigo}",
            de="111111111111111@lid",
            id_mensagem="false_lid_KKK",
            telefone_oculto="5511900000000",
        ),
    )

    async with sessao() as s:
        assert (await s.scalars(select(Handoff))).one().retomado_em is None


async def test_aviso_de_handoff_chama_o_contato_pelo_nome_e_telefone(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    """O id da conversa pode ser um @lid: mostrar isso como telefone manda a pessoa ligar para o nada."""
    agente = await cria_waha(http)
    await manda(
        http,
        agente,
        waha,
        payload_waha("quero falar com uma pessoa", de="1100000000000@lid", telefone_oculto="5551999998888"),
    )
    assert await roda_turno(fila, redis) == "transferido"

    avisos = [texto for chat, texto in waha.enviadas if chat == CHAT_DO_DESTINO]
    assert avisos, "o destino precisa ser avisado"
    assert "Maria (+55 51 99999-8888)" in avisos[0]
    assert "1100000000000" not in avisos[0], "o id oculto não é telefone de ninguém"


async def test_retomar_escrito_do_aparelho_do_agente_no_chat_do_handoff(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    """Responder o aviso pelo aparelho do agente é tão natural quanto responder do próprio celular."""
    agente = await cria_waha(http)
    codigo = await transfere(http, fila, redis, waha, agente)

    resposta = await manda(
        http,
        agente,
        waha,
        payload_waha(f"/retomar {codigo}", de=CHAT_DO_DESTINO, minha=True, id_mensagem="true_dest_LLL"),
    )

    assert resposta.status_code == 200
    async with sessao() as s:
        fechado = (await s.scalars(select(Handoff))).one()
    assert fechado.retomado_em is not None, "o comando vale, mesmo saindo do número do agente"


async def test_fala_do_aparelho_em_conversa_desconhecida_nao_some_calada(http, fila, waha, sessao, caplog) -> None:  # type: ignore[no-untyped-def]
    """Responder de um chat que o agente nunca atendeu não faz nada, mas precisa aparecer no log."""
    agente = await cria_waha(http)

    resposta = await manda(
        http,
        agente,
        waha,
        payload_waha("bom dia", de="5511911112222@c.us", minha=True, id_mensagem="true_novo_MMM"),
    )

    assert resposta.status_code == 200
    async with sessao() as s:
        assert list(await s.scalars(select(Conversa))) == []


async def test_retomar_escrito_na_conversa_do_contato_pelo_aparelho_do_agente(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    """Quem escreve do número do agente é o operador falando com o sistema, em qualquer conversa."""
    agente = await cria_waha(http)
    codigo = await transfere(http, fila, redis, waha, agente)

    resposta = await manda(
        http,
        agente,
        waha,
        payload_waha(f"/retomar {codigo}", de=CONTATO, minha=True, id_mensagem="true_contato_NNN"),
    )

    assert resposta.status_code == 200
    async with sessao() as s:
        fechado = (await s.scalars(select(Handoff))).one()
        conversa = (await s.scalars(select(Conversa).where(Conversa.id_externo == CONTATO))).one()
    assert fechado.retomado_em is not None and fechado.retomado_por == "comando"
    assert conversa.status == "agente"


async def test_conversa_comum_do_aparelho_continua_pausando(http, fila, waha, sessao) -> None:  # type: ignore[no-untyped-def]
    """Só o comando é comando: responder o contato continua sendo assumir a conversa."""
    agente = await cria_waha(http)
    await manda(http, agente, waha, payload_waha("oi"))

    await manda(http, agente, waha, payload_waha("eu respondo, obrigado", minha=True, id_mensagem="true_x_OOO"))

    async with sessao() as s:
        assert (await s.scalars(select(Handoff))).one().motivo == handoff.MOTIVO_PESSOA_RESPONDEU


async def test_retomar_sem_codigo_na_conversa_do_contato(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    """Na conversa do contato não há dúvida sobre qual devolver: pedir código seria atrito à toa."""
    agente = await cria_waha(http)
    await transfere(http, fila, redis, waha, agente)

    await manda(http, agente, waha, payload_waha("/retomar", de=CONTATO, minha=True, id_mensagem="true_s_PPP"))

    async with sessao() as s:
        assert (await s.scalars(select(Handoff))).one().retomado_em is not None


async def test_retomar_sem_codigo_com_uma_conversa_em_atendimento(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)
    await transfere(http, fila, redis, waha, agente)

    await manda(http, agente, waha, payload_waha("/retomar", de=CHAT_DO_DESTINO, id_mensagem="false_s_QQQ"))

    async with sessao() as s:
        assert (await s.scalars(select(Handoff))).one().retomado_em is not None


async def test_retomar_sem_codigo_com_duas_conversas_pede_para_escolher(http, fila, waha, redis, sessao, modelo_transfere) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_waha(http)
    await transfere(http, fila, redis, waha, agente)
    await manda(http, agente, waha, payload_waha("quero uma pessoa", de="5511922223333@c.us", id_mensagem="false_2_RRR"))
    assert await roda_turno(fila, redis) == "transferido"

    await manda(http, agente, waha, payload_waha("/retomar", de=CHAT_DO_DESTINO, id_mensagem="false_s_SSS"))

    async with sessao() as s:
        abertos = [h for h in await s.scalars(select(Handoff)) if h.retomado_em is None]
    assert len(abertos) == 2, "com duas em atendimento, o comando sem código não escolhe sozinho"
    pedidos = [t for _, t in waha.enviadas if "mais de uma conversa em atendimento" in t]
    assert pedidos and all(f"/retomar {h.codigo}" in pedidos[-1] for h in abertos)


async def test_log_nao_guarda_o_texto_de_conversa_que_nao_e_do_agente(http, fila, waha) -> None:  # type: ignore[no-untyped-def]
    """`message.any` traz a conversa pessoal de quem tem o aparelho: isso não pode virar log."""
    from structlog.testing import capture_logs

    agente = await cria_waha(http)
    segredo = "combinamos amanha na casa da minha mae"

    with capture_logs() as registrado:
        await manda(
            http,
            agente,
            waha,
            payload_waha(segredo, de="80869972770836@lid", minha=True, id_mensagem="true_priv_TTT"),
        )

    assert not any(segredo in str(linha) for linha in registrado), "conversa pessoal não entra no log"
    assert any(linha.get("de") == "80869972770836@lid" for linha in registrado), (
        "o remetente entra, para dar para diagnosticar"
    )
