"""O front do painel: como ele é servido e a rota que ele chama primeiro.

O que estes testes seguram: ninguém alcança o painel sem sessão (nem os arquivos do build), rota
interna recarregada não vira 404, caminho com `..` não lê arquivo da VPS, e `/painel/api/eu` não
devolve nada que não seja da tela.
"""

import httpx
import pytest

from app.painel import servico
from testes.conftest import cria_cliente_e_agente, limpa_o_redis_do_painel
from testes.test_painel import SENHA, codigo_novo, entra


@pytest.fixture
async def dentro(painel: httpx.AsyncClient) -> httpx.AsyncClient:
    await entra(painel)
    return painel


# O front


async def test_sem_sessao_o_front_manda_para_o_login(painel: httpx.AsyncClient):
    """Aqui quem bate é navegador de gente: vai para a tela de entrar, não para um 401 cru."""
    resposta = await painel.get("/painel/app")
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/painel/entrar"


async def test_sem_sessao_nem_o_javascript_do_build_sai(painel: httpx.AsyncClient):
    resposta = await painel.get("/painel/app/assets/index-teste.js")
    assert resposta.status_code == 303
    assert "console.log" not in resposta.text


async def test_com_sessao_o_front_abre(dentro: httpx.AsyncClient):
    resposta = await dentro.get("/painel/app")
    assert resposta.status_code == 200
    assert 'id=raiz' in resposta.text
    assert resposta.headers["cache-control"] == "no-store"


async def test_rota_interna_recarregada_devolve_o_indice(dentro: httpx.AsyncClient):
    """`/painel/app/agentes/<id>` não é arquivo: quem conhece essa rota é o React Router."""
    resposta = await dentro.get("/painel/app/agentes/8f3c1a2b/comunicacao")
    assert resposta.status_code == 200
    assert "id=raiz" in resposta.text


async def test_arquivo_do_build_e_servido_com_cache_longo(dentro: httpx.AsyncClient):
    resposta = await dentro.get("/painel/app/assets/index-teste.js")
    assert resposta.status_code == 200
    assert "console.log" in resposta.text
    assert "immutable" in resposta.headers["cache-control"]


async def test_caminho_para_fora_da_pasta_nao_le_arquivo_da_vps(dentro: httpx.AsyncClient):
    """Arquivo acima da pasta do build nunca sai, escrito como for.

    Parte das tentativas o próprio servidor normaliza antes da rota e vira 404; o que este teste
    garante é o resultado: em nenhuma delas o conteúdo de fora aparece na resposta.
    """
    tentativas = (
        "../nao-deve-sair.txt",
        "..%2Fnao-deve-sair.txt",
        "%2e%2e%2fnao-deve-sair.txt",
        "assets/../../nao-deve-sair.txt",
        "../../../etc/hostname",
    )
    for tentativa in tentativas:
        resposta = await dentro.get(f"/painel/app/{tentativa}")
        assert "ISTO-NAO-PODE-SAIR" not in resposta.text, tentativa
        assert resposta.status_code in (200, 404), tentativa


async def test_sem_o_build_o_painel_diz_o_que_fazer(dentro: httpx.AsyncClient, tmp_path, monkeypatch):
    """Imagem subida sem o front construído não pode responder uma página em branco."""
    from app.painel import rotas

    monkeypatch.setattr(rotas, "_pasta_do_front", lambda: tmp_path)
    resposta = await dentro.get("/painel/app")
    assert resposta.status_code == 503
    assert "npm run build" in resposta.text


# GET /painel/api/eu


async def test_api_sem_sessao_responde_401_em_json(painel: httpx.AsyncClient):
    """O front trata o 401 sozinho e manda para o login; por isso aqui não é redirecionamento."""
    resposta = await painel.get("/painel/api/eu")
    assert resposta.status_code == 401
    assert resposta.json()["detail"]


async def test_eu_conta_empresas_e_agentes(
    painel: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_cliente_e_agente(http, "Clínica Exemplo", "Caio")
    await entra(painel)

    dados = (await painel.get("/painel/api/eu")).json()
    assert dados["empresas"] == 2
    assert dados["agentes"] == 2
    assert dados["instalacao"]["subdominio_app"] == "app.teste.local"
    assert dados["operador"]["criado_em"]


async def test_eu_nao_devolve_credencial_nem_token_de_webhook(
    painel: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await entra(painel)

    corpo = (await painel.get("/painel/api/eu")).text
    assert agente["token"] not in corpo
    for proibido in ("credenciais", "senha", "chave", "token_webhook"):
        assert proibido not in corpo.lower()


# Token de escrita


def test_csrf_e_diferente_por_sessao_e_confere():
    de_um = servico.token_csrf("sessao-um")
    de_outro = servico.token_csrf("sessao-outro")
    assert de_um != de_outro
    assert servico.csrf_confere("sessao-um", de_um)
    assert not servico.csrf_confere("sessao-um", de_outro)


def test_csrf_vazio_nunca_passa():
    assert not servico.csrf_confere("", servico.token_csrf(""))
    assert not servico.csrf_confere("sessao-um", "")


async def test_o_csrf_da_resposta_e_o_da_sessao_de_quem_pediu(painel: httpx.AsyncClient):
    await limpa_o_redis_do_painel()
    await painel.post(
        "/painel/primeiro-acesso",
        data={"codigo": await codigo_novo(), "senha": SENHA, "senha2": SENHA},
    )
    cookie = painel.cookies["asimov_painel"]
    dados = (await painel.get("/painel/api/eu")).json()
    assert dados["csrf"] == servico.token_csrf(cookie)
