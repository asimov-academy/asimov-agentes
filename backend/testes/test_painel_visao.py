"""A tela de abertura do painel: `GET /painel/api/empresas` e `GET /painel/api/visao-geral`.

O que estes testes seguram: sem sessão não sai nada, o filtro por empresa vem da URL e é conferido
no banco, uma empresa nunca enxerga o número da outra, dia sem turno vira zero em vez de buraco no
gráfico, e a situação da barra do topo acompanha a falha que apareceu.
"""

import uuid
from datetime import timedelta
from decimal import Decimal
from typing import Any

import httpx
import pytest

from app.consumo.modelos import Falha, Turno
from app.conversas.modelos import Contato, Conversa
from app.handoff.modelos import Handoff
from app.plataforma.banco import agora, fabrica_sessao
from testes.conftest import cria_cliente_e_agente
from testes.test_painel import entra


@pytest.fixture
async def dentro(painel: httpx.AsyncClient) -> httpx.AsyncClient:
    await entra(painel)
    return painel


async def cria_conversa(agente: dict[str, Any], canal: str = "chatwoot") -> Conversa:
    cliente_id = uuid.UUID(agente["cliente_id"])
    agente_id = uuid.UUID(agente["id"])
    async with fabrica_sessao()() as s:
        contato = Contato(
            cliente_id=cliente_id, agente_id=agente_id, id_externo=f"c-{uuid.uuid4()}", nome="Maria"
        )
        s.add(contato)
        await s.flush()
        conversa = Conversa(
            cliente_id=cliente_id,
            agente_id=agente_id,
            contato_id=contato.id,
            id_externo=f"v-{uuid.uuid4()}",
            canal=canal,
        )
        s.add(conversa)
        await s.commit()
        await s.refresh(conversa)
        return conversa


async def cria_turno(
    conversa: Conversa,
    modelo: str = "openai:gpt-4o-mini",
    custo: str = "0.01",
    dias_atras: int = 0,
    funcao: str = "resposta",
) -> None:
    async with fabrica_sessao()() as s:
        s.add(
            Turno(
                cliente_id=conversa.cliente_id,
                conversa_id=conversa.id,
                modelo=modelo,
                funcao=funcao,
                tokens_entrada=100,
                tokens_saida=50,
                custo_estimado=Decimal(custo),
                criado_em=agora() - timedelta(days=dias_atras),
            )
        )
        await s.commit()


async def cria_falha(agente: dict[str, Any], tipo: str, erro: str = "deu ruim") -> None:
    async with fabrica_sessao()() as s:
        s.add(
            Falha(
                cliente_id=uuid.UUID(agente["cliente_id"]),
                agente_id=uuid.UUID(agente["id"]),
                tipo=tipo,
                detalhe={"erro": erro},
            )
        )
        await s.commit()


async def cria_handoff(conversa: Conversa, agente: dict[str, Any], vencido: bool) -> None:
    async with fabrica_sessao()() as s:
        s.add(
            Handoff(
                cliente_id=conversa.cliente_id,
                agente_id=uuid.UUID(agente["id"]),
                conversa_id=conversa.id,
                motivo="o contato pediu",
                resumo="quer falar com gente",
                codigo=uuid.uuid4().hex[:6].upper(),
                retomar_em=agora() + timedelta(hours=-1 if vencido else 4),
            )
        )
        await s.commit()


# Empresas


async def test_empresas_sem_sessao_nao_sai(painel: httpx.AsyncClient):
    assert (await painel.get("/painel/api/empresas")).status_code == 401


async def test_empresas_lista_o_que_a_barra_do_topo_mostra(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_cliente_e_agente(http, "Clínica Exemplo", "Caio")

    empresas = (await dentro.get("/painel/api/empresas")).json()
    assert [e["nome"] for e in empresas] == ["Clínica Exemplo", "Loja Exemplo"]
    assert all(set(e) == {"id", "nome", "slug", "ativo"} for e in empresas)


# Visão geral


async def test_visao_geral_sem_sessao_nao_sai(painel: httpx.AsyncClient):
    assert (await painel.get("/painel/api/visao-geral")).status_code == 401


async def test_periodo_fora_dos_tres_e_recusado(dentro: httpx.AsyncClient):
    resposta = await dentro.get("/painel/api/visao-geral", params={"dias": 90})
    assert resposta.status_code == 422
    assert "1, 7, 30" in resposta.json()["detail"]


async def test_empresa_que_nao_existe_e_404(dentro: httpx.AsyncClient):
    resposta = await dentro.get("/painel/api/visao-geral", params={"cliente_id": str(uuid.uuid4())})
    assert resposta.status_code == 404


async def test_instalacao_vazia_responde_zerada(dentro: httpx.AsyncClient):
    dados = (await dentro.get("/painel/api/visao-geral")).json()
    assert dados["totais"] == {
        "conversas": 0,
        "turnos": 0,
        "custo": "0",
        "custo_parcial": False,
        "falhas": 0,
        "handoffs_vencidos": 0,
    }
    assert dados["modelos"] == []
    assert dados["situacao"]["cor"] == "ok"


async def test_cartoes_e_gasto_por_modelo_somam_o_periodo(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    conversa = await cria_conversa(agente)
    await cria_turno(conversa, custo="0.02")
    await cria_turno(conversa, custo="0.03")
    await cria_turno(conversa, modelo="openai:whisper-1", custo="0.01", funcao="transcricao")
    await cria_turno(conversa, custo="9.99", dias_atras=20)

    dados = (await dentro.get("/painel/api/visao-geral", params={"dias": 7})).json()
    assert dados["totais"]["conversas"] == 1
    assert dados["totais"]["turnos"] == 2, "transcrição soma custo, não turno"
    assert Decimal(dados["totais"]["custo"]) == Decimal("0.06")
    modelos = {m["modelo"]: m for m in dados["modelos"]}
    assert Decimal(modelos["openai:gpt-4o-mini"]["custo"]) == Decimal("0.05")
    assert modelos["openai:whisper-1"]["chamadas"] == 1

    trinta = (await dentro.get("/painel/api/visao-geral", params={"dias": 30})).json()
    assert Decimal(trinta["totais"]["custo"]) == Decimal("10.05")


async def test_modelo_sem_preco_marca_o_custo_como_parcial(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    conversa = await cria_conversa(agente)
    async with fabrica_sessao()() as s:
        s.add(
            Turno(
                cliente_id=conversa.cliente_id,
                conversa_id=conversa.id,
                modelo="groq:llama",
                custo_estimado=None,
            )
        )
        await s.commit()

    dados = (await dentro.get("/painel/api/visao-geral")).json()
    assert dados["totais"]["custo_parcial"] is True


async def test_uma_empresa_nao_ve_o_numero_da_outra(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    loja = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    clinica = await cria_cliente_e_agente(http, "Clínica Exemplo", "Caio")
    await cria_turno(await cria_conversa(loja), custo="0.50")
    await cria_turno(await cria_conversa(clinica), custo="0.10")
    await cria_falha(clinica, "turno_modelo_falhou")

    da_loja = (
        await dentro.get("/painel/api/visao-geral", params={"cliente_id": loja["cliente_id"]})
    ).json()
    assert Decimal(da_loja["totais"]["custo"]) == Decimal("0.50")
    assert da_loja["totais"]["falhas"] == 0
    assert da_loja["falhas"] == []

    tudo = (await dentro.get("/painel/api/visao-geral")).json()
    assert Decimal(tudo["totais"]["custo"]) == Decimal("0.60"), "sem filtro, a instalação inteira"


async def test_dia_sem_turno_vira_zero_em_vez_de_buraco(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    conversa = await cria_conversa(agente)
    await cria_turno(conversa)
    await cria_turno(conversa, dias_atras=3)

    dados = (await dentro.get("/painel/api/visao-geral", params={"dias": 7})).json()
    assert dados["serie"]["por"] == "day"
    assert len(dados["serie"]["pontos"]) == 8, "os sete dias mais o de hoje"
    assert sum(p["turnos"] for p in dados["serie"]["pontos"]) == 2
    assert dados["serie"]["pontos"][-1]["turnos"] == 1


async def test_periodo_de_um_dia_sai_por_hora(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_turno(await cria_conversa(agente))

    dados = (await dentro.get("/painel/api/visao-geral", params={"dias": 1})).json()
    assert dados["serie"]["por"] == "hour"
    assert len(dados["serie"]["pontos"]) == 25
    assert sum(p["turnos"] for p in dados["serie"]["pontos"]) == 1


async def test_handoff_vencido_vem_primeiro_e_conta_no_cartao(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_handoff(await cria_conversa(agente), agente, vencido=False)
    await cria_handoff(await cria_conversa(agente), agente, vencido=True)

    dados = (await dentro.get("/painel/api/visao-geral")).json()
    assert dados["totais"]["handoffs_vencidos"] == 1
    assert [h["vencido"] for h in dados["handoffs"]] == [True, False]
    assert dados["handoffs"][0]["agente"] == "Ana"
    assert dados["handoffs"][0]["cliente"] == "Loja Exemplo"
    assert dados["situacao"]["cor"] == "atencao"


async def test_handoff_nao_devolve_texto_de_conversa(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    """O resumo do handoff é conteúdo de conversa: ele aparece na tela de Chat, não na abertura."""
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_handoff(await cria_conversa(agente), agente, vencido=True)

    corpo = (await dentro.get("/painel/api/visao-geral")).text
    assert "quer falar com gente" not in corpo


async def test_canal_fora_do_ar_deixa_a_barra_vermelha(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_falha(agente, "turno_modelo_falhou")
    amarelo = (await dentro.get("/painel/api/visao-geral")).json()
    assert amarelo["situacao"]["cor"] == "atencao"

    await cria_falha(agente, "canal_fora_do_ar", "sessão parou")
    vermelho = (await dentro.get("/painel/api/visao-geral")).json()
    assert vermelho["situacao"]["cor"] == "perigo"
    assert vermelho["situacao"]["texto"] == "canal fora do ar"


async def test_visao_geral_nao_devolve_credencial(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_turno(await cria_conversa(agente))

    corpo = (await dentro.get("/painel/api/visao-geral")).text
    assert agente["token"] not in corpo
    for proibido in ("credenciais", "token_webhook", "chave"):
        assert proibido not in corpo.lower()


# Comparação com o período anterior, resolução e agentes


async def test_numero_vem_com_o_periodo_anterior_do_lado(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    conversa = await cria_conversa(agente)
    await cria_turno(conversa)
    await cria_turno(conversa)
    await cria_turno(conversa, dias_atras=9)

    dados = (await dentro.get("/painel/api/visao-geral", params={"dias": 7})).json()
    assert dados["totais"]["turnos"] == 2
    assert dados["variacao"]["turnos"] == 100.0, "um turno na semana anterior, dois nesta"


async def test_sem_periodo_anterior_a_variacao_e_nula(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    """Não existe "+100%" sobre zero: a tela escreve "sem comparação" em vez de inventar número."""
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_turno(await cria_conversa(agente))

    dados = (await dentro.get("/painel/api/visao-geral")).json()
    assert dados["variacao"]["turnos"] is None


async def test_resolucao_conta_a_conversa_que_precisou_de_gente(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_conversa(agente)
    await cria_conversa(agente)
    await cria_conversa(agente)
    com_gente = await cria_conversa(agente)
    await cria_handoff(com_gente, agente, vencido=False)

    dados = (await dentro.get("/painel/api/visao-geral")).json()
    assert dados["resolucao"] == {"conversas": 4, "com_gente": 1, "sozinho": 3, "porcento": 75}


async def test_sem_conversa_a_resolucao_nao_inventa_porcento(dentro: httpx.AsyncClient):
    dados = (await dentro.get("/painel/api/visao-geral")).json()
    assert dados["resolucao"]["porcento"] is None


async def test_agentes_saem_do_que_mais_respondeu_para_o_que_menos(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    caio = await cria_cliente_e_agente(http, "Clínica Exemplo", "Caio")
    conversa_da_ana = await cria_conversa(ana)
    await cria_turno(conversa_da_ana)
    conversa_do_caio = await cria_conversa(caio)
    for _ in range(3):
        await cria_turno(conversa_do_caio)

    dados = (await dentro.get("/painel/api/visao-geral")).json()
    assert [(a["agente"], a["turnos"]) for a in dados["agentes"]] == [("Caio", 3), ("Ana", 1)]

    so_da_loja = (
        await dentro.get("/painel/api/visao-geral", params={"cliente_id": ana["cliente_id"]})
    ).json()
    assert [a["agente"] for a in so_da_loja["agentes"]] == ["Ana"]


async def test_falha_sai_resumida_e_nunca_com_o_corpo_do_provedor(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    """O detalhe guarda o que o provedor respondeu, e isso já veio com chave de API dentro."""
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    async with fabrica_sessao()() as s:
        s.add(
            Falha(
                cliente_id=uuid.UUID(agente["cliente_id"]),
                agente_id=uuid.UUID(agente["id"]),
                tipo="turno_modelo_falhou",
                detalhe={"erro": "tempo esgotado", "corpo": {"api_key": "sk-nunca-na-tela"}},
            )
        )
        await s.commit()

    resposta = await dentro.get("/painel/api/visao-geral")
    assert "tempo esgotado" in resposta.text
    assert "sk-nunca-na-tela" not in resposta.text
    assert "api_key" not in resposta.text
    assert resposta.json()["falhas"][0]["resumo"] == "tempo esgotado"
