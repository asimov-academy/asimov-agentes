"""Fase 10, etapas 1 e 2: o ritmo com nome e a persona com o que nunca dizer.

O que estes testes seguram:

- o preset de ritmo escreve os três números, e mexer num número à mão tira o agente do preset;
- a pausa de ler acontece antes do digitando, e não conta como digitação;
- as regras de conversa e de empatia entram em todo turno, sem o operador pedir;
- o que o operador escreveu em "nunca diga" chega ao prompt de sistema.
"""

import random
from typing import Any

import pytest
from pydantic_ai.messages import ModelMessage, ModelResponse
from pydantic_ai.models.function import AgentInfo, FunctionModel
from sqlalchemy import select

from app.conversas import buffer, turno
from app.conversas.divisao import RITMOS, numeros_do_ritmo, pausa_de_leitura
from app.conversas.modelos import Conversa
from testes.conftest import ADMIN, cria_cliente_e_agente, envia_webhook, payload_chatwoot, resposta_falsa


@pytest.fixture
async def redis() -> Any:
    from arq import create_pool
    from arq.connections import RedisSettings

    from app.plataforma.config import config

    pool = await create_pool(RedisSettings.from_dsn(config().redis_url))
    await pool.flushdb()
    yield pool
    await pool.aclose()


@pytest.fixture
def instrucoes(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    vistas: list[str] = []

    def responde(historico: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        vistas.append(info.instructions or "")
        return resposta_falsa(info, ["Oi"])

    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(responde))
    monkeypatch.setattr(turno, "tempos_de_digitacao", lambda textos, *a, **k: [0] * len(textos))
    return vistas


async def roda_um_turno(http, sessao, redis, agente, mensagem_id: int = 1) -> str:  # type: ignore[no-untyped-def]
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=mensagem_id))
    async with sessao() as s:
        conversa = await s.scalar(select(Conversa))
    token = await buffer.agenda_turno(redis, conversa.cliente_id, conversa.id, 1)
    return await turno.processar_turno(
        {"redis": redis}, str(conversa.cliente_id), str(conversa.id), token
    )


# Etapa 1: ritmo


def test_pausa_de_leitura_cresce_com_o_texto_e_respeita_o_teto() -> None:
    sorteio = random.Random(1)
    curta = pausa_de_leitura("oi", "natural", sorteio)
    longa = pausa_de_leitura("a" * 600, "natural", sorteio)
    assert 0.8 <= curta < longa <= RITMOS["natural"]["leitura_maximo_segundos"]
    # No instantâneo não existe pausa: quem escolheu isso quer resposta na hora.
    assert pausa_de_leitura("a" * 600, "instantaneo", sorteio) == 0.0
    # Ritmo desconhecido (o `manual` de quem escolheu os números) lê como o natural.
    assert pausa_de_leitura("a" * 600, "manual", sorteio) > 0


def test_preset_escreve_os_numeros() -> None:
    assert numeros_do_ritmo("reflexivo") == {
        "buffer_segundos": 15,
        "digitacao_caracteres_por_segundo": 4,
        "digitacao_maximo_segundos": 25,
    }
    assert numeros_do_ritmo("manual") == {}


async def test_agente_nasce_natural_e_o_preset_troca_os_numeros(http, canal) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    assert agente["ritmo"] == "natural"
    assert agente["buffer_segundos"] == 8

    caminho = f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}"
    mudado = (await http.patch(caminho, json={"ritmo": "reflexivo"}, headers=ADMIN)).json()
    assert mudado["ritmo"] == "reflexivo"
    assert (mudado["buffer_segundos"], mudado["digitacao_caracteres_por_segundo"]) == (15, 4)


async def test_numero_na_mao_tira_o_agente_do_preset(http, canal) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    caminho = f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}"
    mudado = (await http.patch(caminho, json={"buffer_segundos": 30}, headers=ADMIN)).json()
    assert mudado["ritmo"] == "manual" and mudado["buffer_segundos"] == 30


async def test_ritmo_que_nao_existe_e_recusado(http, canal) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    caminho = f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}"
    assert (await http.patch(caminho, json={"ritmo": "devagar"}, headers=ADMIN)).status_code == 422


async def test_o_turno_espera_a_pausa_de_ler_antes_do_digitando(
    http, canal, fila, sessao, redis, instrucoes, monkeypatch
) -> None:
    """A pausa não conta como digitação: o digitando da primeira mensagem não encolhe por causa dela."""
    from app.conversas import divisao

    esperas: list[float] = []

    async def registra(segundos: float) -> None:
        esperas.append(segundos)

    # A suíte desliga a pausa (é tempo real); aqui ela volta, com valor fixo.
    monkeypatch.setattr(turno, "pausa_de_leitura", lambda *a, **k: 2.5)
    monkeypatch.setattr(turno, "_espera", registra)
    monkeypatch.setattr(divisao, "pausa_de_leitura", lambda *a, **k: 2.5)

    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    assert await roda_um_turno(http, sessao, redis, agente) == "respondido"
    assert esperas and esperas[0] == 2.5


# Etapa 2: persona


async def test_regras_de_conversa_e_empatia_entram_em_todo_turno(
    http, canal, fila, sessao, redis, instrucoes
) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    assert await roda_um_turno(http, sessao, redis, agente) == "respondido"
    prompt = instrucoes[0]
    assert "solicitação está sendo processada" in prompt
    assert "NÃO imite a irritação" in prompt
    assert "preço, prazo ou condição" in prompt


async def test_o_que_ele_nunca_deve_dizer_chega_ao_prompt(http, canal, fila, sessao, redis, instrucoes) -> None:
    """O painel grava pelo mesmo serviço, em `PUT /painel/api/agentes/{id}/perfil`."""
    import uuid

    from app.agentes import servico as agentes_servico

    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    async with sessao() as s:
        _, prompt = await agentes_servico.grava_perfil(
            s,
            uuid.UUID(agente["cliente_id"]),
            uuid.UUID(agente["id"]),
            {
                "funcao": "vendas",
                "sobre_empresa": "Loja de tenis.",
                "nunca_dizer": "- entregamos em 24 horas\nque somos os mais baratos",
            },
        )
    assert "Nunca diga, em nenhuma hipótese:" in prompt
    assert "- entregamos em 24 horas" in prompt

    assert await roda_um_turno(http, sessao, redis, agente) == "respondido"
    assert "entregamos em 24 horas" in instrucoes[0]
    assert "que somos os mais baratos" in instrucoes[0]
