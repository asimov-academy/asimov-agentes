"""Copiloto do painel.

O que estes testes seguram:

- o copiloto só existe com conta de IA vinculada, e sem ela a rota recusa em vez de falhar feio;
- **nenhuma ferramenta do modelo escreve na plataforma**: propor registra proposta e para por aí;
- a escrita só acontece no clique do operador, e passa pelos mesmos serviços do painel;
- o CLI roda com as ferramentas de código desligadas;
- o registro de ferramentas não deixa arquivo solto na pasta, como no catálogo do agente.
"""

import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from app.copiloto import sessao as sessao_do_copiloto
from app.copiloto import servico, vinculo
from app.copiloto.ferramentas import (
    listar_agentes,
    propor_agente_novo,
    propor_mudanca_no_agente,
    registro,
    ver_agente,
)
from app.plataforma.config import config
from testes.conftest import ADMIN, cria_cliente_e_agente
from testes.test_painel import entra


@pytest.fixture(autouse=True)
async def sessao_limpa() -> Any:
    await sessao_do_copiloto.limpa()
    yield
    await sessao_do_copiloto.limpa()


@pytest.fixture
def vinculada(monkeypatch: pytest.MonkeyPatch) -> None:
    """Conta vinculada é um estado do `.env`, escrito por `asimov ia` na VPS."""
    monkeypatch.setattr(config(), "ia_vinculada", True)
    monkeypatch.setattr(config(), "ia_cli", "claude_code")
    monkeypatch.setattr(config(), "ia_conta", "operador@exemplo.com.br")


@pytest.fixture
async def dentro(painel: httpx.AsyncClient) -> httpx.AsyncClient:
    await entra(painel)
    painel.headers["X-Painel-CSRF"] = (await painel.get("/painel/api/eu")).json()["csrf"]
    return painel


# Registro e vínculo


def test_toda_ferramenta_da_pasta_esta_no_registro():
    pasta = Path(registro.__file__).parent
    arquivos = {
        a.stem for a in pasta.glob("*.py") if a.stem not in {"__init__", "base", "registro"}
    }
    assert arquivos == set(registro.CATALOGO), "ferramenta nova precisa de uma linha em FICHAS"


def test_sem_vinculo_o_copiloto_se_declara_desligado():
    assert vinculo.disponivel() is False
    assert vinculo.situacao()["comando"] == "asimov ia"


async def test_copiloto_exige_login_do_painel(painel: httpx.AsyncClient):
    assert (await painel.get("/painel/api/copiloto")).status_code == 401


async def test_sem_conta_vinculada_a_rota_recusa_com_recado(dentro: httpx.AsyncClient):
    estado = (await dentro.get("/painel/api/copiloto")).json()
    assert estado["vinculo"]["vinculada"] is False

    resposta = await dentro.post("/painel/api/copiloto/mensagens", json={"texto": "oi"})
    assert resposta.status_code == 409
    assert "asimov ia" in resposta.json()["detail"]


async def test_com_conta_vinculada_a_mensagem_vai_para_a_fila(
    dentro: httpx.AsyncClient, vinculada: None, fila: Any
):
    resposta = await dentro.post(
        "/painel/api/copiloto/mensagens", json={"texto": "crie um agente de vendas"}
    )
    assert resposta.status_code == 200
    corpo = resposta.json()
    assert corpo["estado"] == "pensando"
    assert corpo["mensagens"][-1] == {
        **corpo["mensagens"][-1],
        "autor": "operador",
        "texto": "crie um agente de vendas",
    }
    assert fila.jobs and fila.jobs[0][0] == "turno_do_copiloto"


async def test_nao_aceita_dois_pedidos_ao_mesmo_tempo(
    dentro: httpx.AsyncClient, vinculada: None, fila: Any
):
    await dentro.post("/painel/api/copiloto/mensagens", json={"texto": "primeiro"})
    segundo = await dentro.post("/painel/api/copiloto/mensagens", json={"texto": "segundo"})
    assert segundo.status_code == 409


# Ferramentas de leitura


async def test_ferramentas_de_leitura_mostram_o_que_existe(http: httpx.AsyncClient, canal: Any):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Luiz")

    lista = json.loads(await listar_agentes.listar_agentes())
    assert [a["nome"] for a in lista] == ["Luiz"]
    assert lista[0]["empresa"] == "Loja Exemplo"

    ficha = await ver_agente.ver_agente(agente["id"])
    assert "Luiz" in ficha
    # O prompt do agente é material do operador: chega delimitado, nunca solto no meio do texto.
    assert "<prompt>" in ficha


async def test_ver_agente_com_id_inventado_nao_quebra():
    assert "não encontrado" in await ver_agente.ver_agente("nao-e-um-id")


# Propor não muda nada


async def test_propor_mudanca_nao_toca_no_agente(http: httpx.AsyncClient, canal: Any):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Luiz")
    recado = await propor_mudanca_no_agente.propor_mudanca_no_agente(
        agente_id=agente["id"], resumo="deixar o tom mais simpático", nome="Luiza"
    )
    assert "confirmar no painel" in recado

    ficha = (await http.get(f"/admin/agentes", headers=ADMIN)).json()
    assert ficha[0]["nome"] == "Luiz", "o agente não pode mudar antes do clique do operador"
    sessao = await sessao_do_copiloto.ler()
    assert sessao["propostas"][0]["situacao"] == "aguardando"


async def test_proposta_com_ferramenta_inexistente_volta_para_o_modelo(http: httpx.AsyncClient, canal: Any):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Luiz")
    recado = await propor_mudanca_no_agente.propor_mudanca_no_agente(
        agente_id=agente["id"], resumo="ligar tudo", ferramentas=["telepatia"]
    )
    assert "telepatia" in recado
    assert (await sessao_do_copiloto.ler())["propostas"] == []


async def test_proposta_de_agente_novo_exige_empresa_que_existe():
    recado = await propor_agente_novo.propor_agente_novo(
        empresa_id="00000000-0000-0000-0000-000000000000",
        nome="Ana",
        resumo="atende no site",
        prompt="Você é a Ana.",
    )
    assert "não encontrada" in recado
    assert (await sessao_do_copiloto.ler())["propostas"] == []


# O clique do operador


async def test_operador_confirma_e_a_mudanca_acontece(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, vinculada: None, canal: Any
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Luiz")
    await propor_mudanca_no_agente.propor_mudanca_no_agente(
        agente_id=agente["id"],
        resumo="tom mais simpático e prompt novo",
        nome="Luiza",
        prompt="Você é a Luiza, da Loja Exemplo.",
    )
    proposta = (await sessao_do_copiloto.ler())["propostas"][0]

    resposta = await dentro.post(
        f"/painel/api/copiloto/propostas/{proposta['id']}", json={"aplicar": True}
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["propostas"][0]["situacao"] == "aplicada"

    ficha = (await dentro.get(f"/painel/api/agentes/{agente['id']}")).json()
    assert ficha["nome"] == "Luiza"
    prompt = (await dentro.get(f"/painel/api/agentes/{agente['id']}/prompt")).json()
    assert "Luiza" in prompt["texto"]


async def test_operador_recusa_e_nada_muda(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, vinculada: None, canal: Any
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Luiz")
    await propor_mudanca_no_agente.propor_mudanca_no_agente(
        agente_id=agente["id"], resumo="mudar o nome", nome="Luiza"
    )
    proposta = (await sessao_do_copiloto.ler())["propostas"][0]

    resposta = await dentro.post(
        f"/painel/api/copiloto/propostas/{proposta['id']}", json={"aplicar": False}
    )
    assert resposta.json()["propostas"][0]["situacao"] == "recusada"
    assert (await dentro.get(f"/painel/api/agentes/{agente['id']}")).json()["nome"] == "Luiz"


async def test_proposta_nao_se_aplica_duas_vezes(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, vinculada: None, canal: Any
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Luiz")
    await propor_mudanca_no_agente.propor_mudanca_no_agente(
        agente_id=agente["id"], resumo="mudar o nome", nome="Luiza"
    )
    proposta = (await sessao_do_copiloto.ler())["propostas"][0]
    caminho = f"/painel/api/copiloto/propostas/{proposta['id']}"
    assert (await dentro.post(caminho, json={"aplicar": True})).status_code == 200
    assert (await dentro.post(caminho, json={"aplicar": True})).status_code == 409


async def test_agente_novo_nasce_no_canal_nativo(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, vinculada: None
):
    empresa = (await http.post("/admin/clientes", json={"nome": "Loja Exemplo"}, headers=ADMIN)).json()
    await propor_agente_novo.propor_agente_novo(
        empresa_id=empresa["id"],
        nome="Ana",
        resumo="atende quem chega pelo site",
        prompt="Você é a Ana, da Loja Exemplo.",
    )
    proposta = (await sessao_do_copiloto.ler())["propostas"][0]
    resposta = await dentro.post(
        f"/painel/api/copiloto/propostas/{proposta['id']}", json={"aplicar": True}
    )
    assert resposta.status_code == 200, resposta.text

    agentes = (await dentro.get("/painel/api/agentes")).json()
    assert [(a["nome"], a["canal"]) for a in agentes] == [("Ana", "nativo")]


# O servidor MCP, que é a fronteira entre o CLI e a plataforma


async def test_o_mcp_expoe_exatamente_o_registro():
    from app.copiloto.mcp import monta

    tools = await monta().list_tools()
    assert [t.name for t in tools] == [f.nome for f in registro.FICHAS]
    # A descrição que o modelo lê é a docstring, com o quando usar, e não a linha curta do painel.
    propor = next(t for t in tools if t.name == "propor_mudanca_no_agente")
    assert "confirmar no painel" in (propor.description or "")
    assert "agente_id" in propor.input_schema["properties"]


# O comando do CLI


def test_o_cli_roda_sem_as_ferramentas_de_codigo():
    linha = servico.comando("claude", "oi")
    assert "--disallowedTools" in linha
    assert "Bash" in linha[linha.index("--disallowedTools") + 1]
    assert linha[linha.index("--allowedTools") + 1] == "mcp__asimov"
    # `--strict-mcp-config` impede que um mcp.json do operador entre junto.
    assert "--strict-mcp-config" in linha


def test_o_codex_roda_em_leitura_e_com_o_nosso_mcp():
    linha = servico.comando("codex", "oi")
    assert linha[:3] == ["codex", "exec", "--json"]
    assert linha[linha.index("--sandbox") + 1] == "read-only"
    assert any("mcp_servers.asimov" in p for p in linha)


def test_turno_seguinte_retoma_a_mesma_conversa():
    assert "--resume" in servico.comando("claude", "oi", "sessao-1")
    assert servico.comando("codex", "oi", "sessao-1")[2:4] == ["resume", "--last"]


def test_resposta_do_claude_e_do_codex_viram_texto():
    claude = json.dumps({"result": "pronto", "session_id": "s1"}).encode()
    assert servico._le_claude(claude) == ("pronto", "s1")

    codex = b"\n".join([
        json.dumps({"session_id": "c1", "msg": {"type": "task_started"}}).encode(),
        json.dumps({"msg": {"type": "agent_message", "message": "pronto"}}).encode(),
    ])
    assert servico._le_codex(codex) == ("pronto", "c1")


def test_erro_do_cli_vira_recado_em_portugues():
    assert "asimov ia" in servico._motivo("Error: 401 invalid credentials")
    assert "limite" in servico._motivo("429 rate_limit_exceeded")
    assert "não conseguiu" in servico._motivo("panic: algo estranho")
