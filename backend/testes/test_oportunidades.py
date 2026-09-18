"""Funil: kanban por empresa, cartões e etiquetas.

O que estes testes seguram: o quadro nasce com colunas, nada atravessa a linha de uma empresa para
outra, coluna com cartão não some sem aviso e arrastar um cartão o põe no fim da coluna nova.
"""

import httpx
import pytest

from testes.conftest import ADMIN
from testes.test_painel import entra


@pytest.fixture
async def dentro(painel: httpx.AsyncClient) -> httpx.AsyncClient:
    await entra(painel)
    painel.headers["X-Painel-CSRF"] = (await painel.get("/painel/api/eu")).json()["csrf"]
    return painel


async def empresa(http: httpx.AsyncClient, nome: str = "Loja Exemplo") -> str:
    return (await http.post("/admin/clientes", json={"nome": nome}, headers=ADMIN)).json()["id"]


def funil(cliente_id: str) -> str:
    return f"/painel/api/empresas/{cliente_id}/funil"


async def test_o_quadro_nasce_com_as_colunas_padrao(dentro: httpx.AsyncClient, http: httpx.AsyncClient):
    """Quadro vazio não serve: coluna nenhuma não desenha kanban nenhum."""
    cliente = await empresa(http)
    quadro = (await dentro.get(funil(cliente))).json()

    assert [e["nome"] for e in quadro["etapas"]] == ["Novo", "Em conversa", "Proposta", "Ganho", "Perdido"]
    assert [e["ganha"] for e in quadro["etapas"]][3] is True
    assert [e["perdida"] for e in quadro["etapas"]][4] is True
    assert quadro["oportunidades"] == []
    assert quadro["etiquetas"] == []


async def test_cria_oportunidade_e_ela_cai_na_primeira_coluna(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient
):
    cliente = await empresa(http)
    await dentro.get(funil(cliente))
    resposta = await dentro.post(funil(cliente) + "/oportunidades", json={"titulo": "Orçamento de junho", "valor": "1500.00"})
    assert resposta.status_code == 201, resposta.text

    quadro = (await dentro.get(funil(cliente))).json()
    assert len(quadro["oportunidades"]) == 1
    cartao = quadro["oportunidades"][0]
    assert cartao["titulo"] == "Orçamento de junho"
    assert cartao["valor"] == "1500.00"
    assert cartao["etapa_id"] == quadro["etapas"][0]["id"]
    assert quadro["etapas"][0]["total"] == "1500.00"


async def test_arrastar_para_outra_coluna_poe_o_cartao_no_fim(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient
):
    cliente = await empresa(http)
    quadro = (await dentro.get(funil(cliente))).json()
    proposta = quadro["etapas"][2]["id"]

    primeiro = (await dentro.post(funil(cliente) + "/oportunidades", json={"titulo": "Um", "etapa_id": proposta})).json()["id"]
    segundo = (await dentro.post(funil(cliente) + "/oportunidades", json={"titulo": "Dois"})).json()["id"]

    movido = await dentro.patch(funil(cliente) + f"/oportunidades/{segundo}", json={"etapa_id": proposta})
    assert movido.status_code == 200, movido.text

    quadro = (await dentro.get(funil(cliente))).json()
    na_proposta = [o for o in quadro["oportunidades"] if o["etapa_id"] == proposta]
    assert [o["titulo"] for o in sorted(na_proposta, key=lambda o: o["ordem"])] == ["Um", "Dois"]
    assert {o["id"] for o in na_proposta} == {primeiro, segundo}


async def test_etiqueta_entra_e_sai_do_cartao(dentro: httpx.AsyncClient, http: httpx.AsyncClient):
    cliente = await empresa(http)
    await dentro.get(funil(cliente))
    etiqueta = (await dentro.post(funil(cliente) + "/etiquetas", json={"nome": "Urgente", "cor": "perigo"})).json()
    oportunidade = (await dentro.post(funil(cliente) + "/oportunidades", json={"titulo": "Com etiqueta", "etiquetas": [etiqueta["id"]]})).json()

    quadro = (await dentro.get(funil(cliente))).json()
    assert quadro["oportunidades"][0]["etiquetas"] == [etiqueta["id"]]

    await dentro.patch(funil(cliente) + f"/oportunidades/{oportunidade['id']}", json={"etiquetas": []})
    quadro = (await dentro.get(funil(cliente))).json()
    assert quadro["oportunidades"][0]["etiquetas"] == []


async def test_apagar_etiqueta_a_tira_dos_cartoes(dentro: httpx.AsyncClient, http: httpx.AsyncClient):
    cliente = await empresa(http)
    await dentro.get(funil(cliente))
    etiqueta = (await dentro.post(funil(cliente) + "/etiquetas", json={"nome": "Sumiço"})).json()
    await dentro.post(funil(cliente) + "/oportunidades", json={"titulo": "Marcada", "etiquetas": [etiqueta["id"]]})

    apagada = await dentro.delete(funil(cliente) + f"/etiquetas/{etiqueta['id']}")
    assert apagada.status_code == 204

    quadro = (await dentro.get(funil(cliente))).json()
    assert quadro["etiquetas"] == []
    assert quadro["oportunidades"][0]["etiquetas"] == []


async def test_cor_fora_da_paleta_e_recusada(dentro: httpx.AsyncClient, http: httpx.AsyncClient):
    """Etiqueta com hexadecimal solto estragaria a paleta do painel inteiro."""
    cliente = await empresa(http)
    await dentro.get(funil(cliente))
    resposta = await dentro.post(funil(cliente) + "/etiquetas", json={"nome": "Roxa", "cor": "#ff00ff"})
    assert resposta.status_code == 422


async def test_coluna_com_cartao_nao_some_sem_aviso(dentro: httpx.AsyncClient, http: httpx.AsyncClient):
    cliente = await empresa(http)
    quadro = (await dentro.get(funil(cliente))).json()
    primeira = quadro["etapas"][0]["id"]
    await dentro.post(funil(cliente) + "/oportunidades", json={"titulo": "Segurando a coluna"})

    recusada = await dentro.delete(funil(cliente) + f"/etapas/{primeira}")
    assert recusada.status_code == 409
    assert "mova para outra coluna" in recusada.json()["detail"]

    vazia = quadro["etapas"][4]["id"]
    assert (await dentro.delete(funil(cliente) + f"/etapas/{vazia}")).status_code == 204


async def test_o_funil_de_uma_empresa_nao_aparece_na_outra(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient
):
    """A regra que não muda: toda consulta filtra por `cliente_id`."""
    uma = await empresa(http, "Loja Exemplo")
    outra = await empresa(http, "Clínica Exemplo")
    await dentro.get(funil(uma))
    await dentro.get(funil(outra))
    await dentro.post(funil(uma) + "/oportunidades", json={"titulo": "Só da Loja"})

    quadro = (await dentro.get(funil(outra))).json()
    assert quadro["oportunidades"] == []


async def test_etiqueta_de_outra_empresa_nao_cola_no_cartao(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient
):
    uma = await empresa(http, "Loja Exemplo")
    outra = await empresa(http, "Clínica Exemplo")
    await dentro.get(funil(uma))
    await dentro.get(funil(outra))
    alheia = (await dentro.post(funil(outra) + "/etiquetas", json={"nome": "Da outra"})).json()

    criada = await dentro.post(funil(uma) + "/oportunidades", json={"titulo": "Tentando", "etiquetas": [alheia["id"]]})
    assert criada.status_code == 201

    quadro = (await dentro.get(funil(uma))).json()
    assert quadro["oportunidades"][0]["etiquetas"] == []


async def test_cartao_de_outra_empresa_nao_se_move_pela_url_errada(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient
):
    uma = await empresa(http, "Loja Exemplo")
    outra = await empresa(http, "Clínica Exemplo")
    await dentro.get(funil(uma))
    await dentro.get(funil(outra))
    alheio = (await dentro.post(funil(outra) + "/oportunidades", json={"titulo": "Da outra"})).json()["id"]

    resposta = await dentro.patch(funil(uma) + f"/oportunidades/{alheio}", json={"titulo": "Roubado"})
    assert resposta.status_code == 404


async def test_o_funil_exige_sessao(painel: httpx.AsyncClient, http: httpx.AsyncClient):
    cliente = await empresa(http)
    assert (await painel.get(funil(cliente))).status_code == 401


async def test_empresa_que_nao_existe_responde_404(dentro: httpx.AsyncClient):
    import uuid

    assert (await dentro.get(funil(str(uuid.uuid4())))).status_code == 404
