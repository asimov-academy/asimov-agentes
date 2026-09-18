"""Chave de provedor de IA guardada cifrada no banco, e modelo escolhido por agente.

A instalação não pergunta mais modelo: a chave chega ao criar o agente, no terminal ou no painel,
e tem de valer na hora, sem reiniciar a API.
"""

from typing import Any

import httpx
import pytest
from sqlalchemy import select

from app.acessos.modelos import ChaveProvedor
from app.ia import chaves
from app.ia.provedores import ModeloInvalido
from app.plataforma.config import Config, config
from testes.conftest import ADMIN

MODELOS_DA_ANTHROPIC = {"data": [{"id": "claude-sonnet-5"}, {"id": "claude-haiku-4-5"}, {"id": "claude-antigo-1"}]}


@pytest.fixture(autouse=True)
def provedor_falso(monkeypatch: pytest.MonkeyPatch) -> Any:
    """Nenhum teste fala com provedor de verdade. `boa` é a única chave aceita."""
    chamadas: list[tuple[str, str]] = []

    async def consulta(provedor: str, chave: str) -> httpx.Response:
        chamadas.append((provedor, chave))
        pedido = httpx.Request("GET", "https://provedor.exemplo/models")
        if chave != "boa" and chave != "sk-teste":
            return httpx.Response(401, json={}, request=pedido)
        return httpx.Response(200, json=MODELOS_DA_ANTHROPIC, request=pedido)

    monkeypatch.setattr(chaves, "_consulta", consulta)
    chaves._guardadas.clear()
    yield chamadas
    chaves._guardadas.clear()


def sem_padrao_no_env() -> Config:
    return config().model_copy(
        update={"modelo_conversa": "", "modelo_fallback": "", "modelo_visao": "", "modelo_transcricao": ""}
    )


async def test_chave_boa_e_guardada_cifrada_e_nunca_volta(http: httpx.AsyncClient, sessao: Any) -> None:
    resp = await http.put("/admin/ia/chaves/anthropic", json={"chave": "boa"}, headers=ADMIN)
    assert resp.status_code == 204, resp.text

    lista = (await http.get("/admin/ia/chaves", headers=ADMIN)).json()
    assert "anthropic" in lista["com_chave"]
    assert "boa" not in str(lista)

    async with sessao() as s:
        guardada = await s.scalar(select(ChaveProvedor.chave_cifrada))
    assert guardada and "boa" not in guardada


async def test_chave_recusada_pelo_provedor_nao_e_guardada(http: httpx.AsyncClient) -> None:
    resp = await http.put("/admin/ia/chaves/anthropic", json={"chave": "errada"}, headers=ADMIN)
    assert resp.status_code == 422
    assert "anthropic" not in (await http.get("/admin/ia/chaves", headers=ADMIN)).json()["com_chave"]


async def test_provedor_desconhecido_e_recusado(http: httpx.AsyncClient) -> None:
    resp = await http.put("/admin/ia/chaves/outro", json={"chave": "boa"}, headers=ADMIN)
    assert resp.status_code == 422


async def test_rotas_de_chave_exigem_a_chave_admin(http: httpx.AsyncClient) -> None:
    assert (await http.get("/admin/ia/chaves")).status_code == 401
    assert (await http.put("/admin/ia/chaves/openai", json={"chave": "boa"})).status_code == 401


async def test_lista_modelos_com_sugestoes_primeiro(http: httpx.AsyncClient) -> None:
    await http.put("/admin/ia/chaves/anthropic", json={"chave": "boa"}, headers=ADMIN)
    resp = await http.get("/admin/ia/modelos/anthropic", params={"funcao": "conversa"}, headers=ADMIN)
    assert resp.status_code == 200, resp.text
    assert resp.json()[:2] == ["anthropic:claude-sonnet-5", "anthropic:claude-haiku-4-5"]

    sem_chave = await http.get("/admin/ia/modelos/gemini", headers=ADMIN)
    assert sem_chave.status_code == 422
    audio = await http.get("/admin/ia/modelos/anthropic", params={"funcao": "transcricao"}, headers=ADMIN)
    assert audio.status_code == 422


def test_filtro_separa_audio_de_conversa() -> None:
    ids = ["gpt-5.1", "whisper-1", "gpt-4o-transcribe", "text-embedding-3", "gpt-5-mini", "dall-e-3"]
    assert chaves.filtra("openai", "transcricao", ids) == ["gpt-4o-transcribe", "whisper-1"]
    assert chaves.filtra("openai", "conversa", ids) == ["gpt-5.1", "gpt-5-mini"]


async def test_agente_nasce_com_o_modelo_escolhido_e_o_resto_no_mesmo_provedor(http: httpx.AsyncClient) -> None:
    await http.put("/admin/ia/chaves/anthropic", json={"chave": "boa"}, headers=ADMIN)
    cliente = (await http.post("/admin/clientes", json={"nome": "Loja Exemplo"}, headers=ADMIN)).json()
    resp = await http.post(
        f"/admin/clientes/{cliente['id']}/agentes",
        json={"nome": "Ana", "canal": "nativo", "modelos": {"modelo_conversa": "anthropic:claude-sonnet-5"}},
        headers=ADMIN,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["modelo_conversa"] == "anthropic:claude-sonnet-5"


def test_instalacao_nova_completa_os_modelos_a_partir_da_resposta() -> None:
    cfg = sem_padrao_no_env()
    final = chaves.completa({"modelo_conversa": "openai:gpt-5.1"}, cfg)
    assert final["modelo_auxiliar"] == "openai:gpt-5-mini"
    assert final["modelo_visao"] == "openai:gpt-5-mini"
    assert final["modelo_transcricao"] == "openai:gpt-4o-transcribe"
    assert final["modelo_fallback"] is None


def test_resposta_na_anthropic_transcreve_em_outro_provedor_com_chave() -> None:
    chaves._guardadas["anthropic"] = "boa"
    final = chaves.completa({"modelo_conversa": "anthropic:claude-sonnet-5"}, sem_padrao_no_env())
    # O `.env` de teste tem chave da OpenAI e da Groq; a OpenAI vem primeiro.
    assert final["modelo_transcricao"] == "openai:gpt-4o-transcribe"


def test_sem_modelo_de_resposta_a_criacao_e_recusada() -> None:
    with pytest.raises(ModeloInvalido):
        chaves.completa({}, sem_padrao_no_env())


async def test_chave_guardada_pela_api_vale_no_worker(http: httpx.AsyncClient, sessao: Any) -> None:
    """A API e o worker são processos diferentes: o turno relê as chaves do banco."""
    await http.put("/admin/ia/chaves/gemini", json={"chave": "boa"}, headers=ADMIN)
    chaves._guardadas.clear()
    assert chaves.chave_do_provedor("gemini") == ""
    async with sessao() as s:
        await chaves.carregar(s)
    assert chaves.chave_do_provedor("gemini") == "boa"
