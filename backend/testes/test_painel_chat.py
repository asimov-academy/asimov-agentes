"""Chat e contatos no painel: lista de conversas, histórico, devolver ao agente e busca.

O que estes testes seguram: sem sessão não sai nada, o filtro por empresa confere a empresa, a
conversa de uma empresa não aparece na lista da outra, o histórico traz o turno com o custo, e a
busca de contato acha pelo telefone digitado com traço e parêntese.
"""

import uuid
from datetime import timedelta
from decimal import Decimal

import httpx
import pytest

from app.consumo.modelos import Turno
from app.conversas.modelos import Contato, Conversa, Mensagem
from app.plataforma.banco import agora, fabrica_sessao
from testes.conftest import cria_cliente_e_agente
from testes.test_painel import entra


@pytest.fixture
async def dentro(painel: httpx.AsyncClient) -> httpx.AsyncClient:
    await entra(painel)
    painel.headers["X-Painel-CSRF"] = (await painel.get("/painel/api/eu")).json()["csrf"]
    return painel


async def cria_conversa(
    agente: dict, nome: str = "Maria", telefone: str = "5511999990000", status: str = "agente"
) -> Conversa:
    cliente_id = uuid.UUID(agente["cliente_id"])
    async with fabrica_sessao()() as s:
        contato = Contato(
            cliente_id=cliente_id,
            agente_id=uuid.UUID(agente["id"]),
            id_externo=f"c-{uuid.uuid4()}",
            nome=nome,
            telefone=telefone,
        )
        s.add(contato)
        await s.flush()
        conversa = Conversa(
            cliente_id=cliente_id,
            agente_id=uuid.UUID(agente["id"]),
            contato_id=contato.id,
            id_externo=f"v-{uuid.uuid4()}",
            canal="chatwoot",
            status=status,
        )
        s.add(conversa)
        await s.commit()
        await s.refresh(conversa)
        return conversa


async def cria_mensagem(conversa: Conversa, texto: str, autor: str = "contato") -> None:
    async with fabrica_sessao()() as s:
        s.add(
            Mensagem(
                cliente_id=conversa.cliente_id,
                conversa_id=conversa.id,
                direcao="entrada" if autor == "contato" else "saida",
                autor=autor,
                texto=texto,
                criado_em=agora() - timedelta(seconds=10),
            )
        )
        await s.commit()


# Conversas


async def test_conversas_sem_sessao_nao_saem(painel: httpx.AsyncClient):
    assert (await painel.get("/painel/api/conversas")).status_code == 401


async def test_lista_traz_contato_agente_e_empresa(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_conversa(agente)

    lista = (await dentro.get("/painel/api/conversas")).json()
    assert len(lista) == 1
    assert lista[0]["contato"] == "Maria"
    assert lista[0]["agente"] == "Ana"
    assert lista[0]["empresa"] == "Loja Exemplo"


async def test_conversa_de_uma_empresa_nao_aparece_na_da_outra(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    loja = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    clinica = await cria_cliente_e_agente(http, "Clínica Exemplo", "Caio")
    await cria_conversa(loja, nome="Maria")
    await cria_conversa(clinica, nome="João")

    da_loja = (
        await dentro.get("/painel/api/conversas", params={"cliente_id": loja["cliente_id"]})
    ).json()
    assert [c["contato"] for c in da_loja] == ["Maria"]
    assert len((await dentro.get("/painel/api/conversas")).json()) == 2


async def test_filtro_por_agente_e_por_situacao(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_conversa(agente, nome="Maria", status="agente")
    await cria_conversa(agente, nome="Pedro", status="humano")

    com_gente = (await dentro.get("/painel/api/conversas", params={"status": "humano"})).json()
    assert [c["contato"] for c in com_gente] == ["Pedro"]

    do_agente = (
        await dentro.get("/painel/api/conversas", params={"agente_id": agente["id"]})
    ).json()
    assert len(do_agente) == 2


async def test_historico_traz_as_mensagens_e_o_turno(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    conversa = await cria_conversa(agente)
    await cria_mensagem(conversa, "oi, preciso de ajuda")
    await cria_mensagem(conversa, "claro, já verifico", autor="agente")
    async with fabrica_sessao()() as s:
        s.add(
            Turno(
                cliente_id=conversa.cliente_id,
                conversa_id=conversa.id,
                modelo="openai:gpt-4o-mini",
                tokens_entrada=120,
                tokens_saida=40,
                custo_estimado=Decimal("0.0031"),
                latencia_ms=820,
            )
        )
        await s.commit()

    ficha = (await dentro.get(f"/painel/api/conversas/{conversa.id}")).json()
    assert [m["texto"] for m in ficha["mensagens"]] == ["oi, preciso de ajuda", "claro, já verifico"]
    assert ficha["turnos"][0]["modelo"] == "openai:gpt-4o-mini"
    assert Decimal(ficha["turnos"][0]["custo_estimado"]) == Decimal("0.0031")
    assert ficha["contato"] == "Maria"


async def test_conversa_que_nao_existe_e_404(dentro: httpx.AsyncClient):
    assert (await dentro.get(f"/painel/api/conversas/{uuid.uuid4()}")).status_code == 404


async def test_retomar_devolve_a_conversa_ao_agente(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    conversa = await cria_conversa(agente, status="humano")

    resposta = await dentro.post(f"/painel/api/conversas/{conversa.id}/retomar", json={})
    assert resposta.status_code == 200, resposta.text

    depois = (await dentro.get(f"/painel/api/conversas/{conversa.id}")).json()
    assert depois["status"] == "agente"


async def test_retomar_sem_csrf_nao_passa(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    conversa = await cria_conversa(agente, status="humano")
    resposta = await dentro.post(
        f"/painel/api/conversas/{conversa.id}/retomar",
        json={},
        headers={"X-Painel-CSRF": "inventado"},
    )
    assert resposta.status_code == 403


# Contatos


async def test_contatos_sem_sessao_nao_saem(painel: httpx.AsyncClient):
    assert (await painel.get("/painel/api/contatos")).status_code == 401


async def test_busca_por_nome_e_por_telefone_com_pontuacao(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_conversa(agente, nome="Maria Silva", telefone="5511999990000")
    await cria_conversa(agente, nome="João Souza", telefone="5521888887777")

    por_nome = (await dentro.get("/painel/api/contatos", params={"busca": "maria"})).json()
    assert [c["nome"] for c in por_nome] == ["Maria Silva"]

    por_telefone = (
        await dentro.get("/painel/api/contatos", params={"busca": "(21) 88888-7777"})
    ).json()
    assert [c["nome"] for c in por_telefone] == ["João Souza"]


async def test_ficha_do_contato_traz_as_conversas_dele(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    conversa = await cria_conversa(agente, nome="Maria")

    lista = (await dentro.get("/painel/api/contatos")).json()
    ficha = (await dentro.get(f"/painel/api/contatos/{lista[0]['id']}")).json()
    assert ficha["nome"] == "Maria"
    assert ficha["agente"] == "Ana"
    assert [c["id"] for c in ficha["conversas"]] == [str(conversa.id)]


async def test_contato_que_nao_existe_e_404(dentro: httpx.AsyncClient):
    assert (await dentro.get(f"/painel/api/contatos/{uuid.uuid4()}")).status_code == 404
