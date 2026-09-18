"""Agentes pelo painel: lista, criação, ficha, edição e remoção.

O que estes testes seguram: sem sessão não sai nada, o painel usa o mesmo serviço do terminal (o
agente criado aqui aparece no `/admin/agentes`), credencial de canal nunca sai em claro, o filtro
por empresa confere a empresa no banco, e remover exige o nome digitado.
"""

import uuid

import httpx
import pytest

from testes.conftest import ADMIN, CONEXAO_EXEMPLO, cria_cliente_e_agente
from testes.test_painel import entra


@pytest.fixture
async def dentro(painel: httpx.AsyncClient) -> httpx.AsyncClient:
    """Entra e já carrega o token de escrita, como o front faz na primeira chamada."""
    await entra(painel)
    painel.headers["X-Painel-CSRF"] = (await painel.get("/painel/api/eu")).json()["csrf"]
    return painel


async def cria_empresa(dentro: httpx.AsyncClient, nome: str) -> dict:
    resposta = await dentro.post("/painel/api/empresas", json={"nome": nome})
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


# Empresas


async def test_empresa_sem_sessao_nao_nasce(painel: httpx.AsyncClient):
    assert (await painel.post("/painel/api/empresas", json={"nome": "Loja"})).status_code == 401


async def test_empresa_criada_pelo_painel_aparece_na_lista(dentro: httpx.AsyncClient):
    criada = await cria_empresa(dentro, "Loja Exemplo")
    assert criada["slug"] == "loja-exemplo"
    empresas = (await dentro.get("/painel/api/empresas")).json()
    assert [e["id"] for e in empresas] == [criada["id"]]


async def test_empresa_repetida_e_409(dentro: httpx.AsyncClient):
    await cria_empresa(dentro, "Loja Exemplo")
    resposta = await dentro.post("/painel/api/empresas", json={"nome": "Loja Exemplo"})
    assert resposta.status_code == 409


# Lista


async def test_lista_sem_sessao_nao_sai(painel: httpx.AsyncClient):
    assert (await painel.get("/painel/api/agentes")).status_code == 401


async def test_lista_traz_o_nome_da_empresa_em_cada_linha(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_cliente_e_agente(http, "Clínica Exemplo", "Caio")

    agentes = (await dentro.get("/painel/api/agentes")).json()
    assert [(a["nome"], a["empresa"]) for a in agentes] == [
        ("Caio", "Clínica Exemplo"),
        ("Ana", "Loja Exemplo"),
    ]


async def test_filtro_por_empresa_e_por_situacao(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_cliente_e_agente(http, "Clínica Exemplo", "Caio")

    da_loja = (
        await dentro.get("/painel/api/agentes", params={"cliente_id": ana["cliente_id"]})
    ).json()
    assert [a["nome"] for a in da_loja] == ["Ana"]

    await dentro.patch(f"/painel/api/agentes/{ana['id']}", json={"ativo": False})
    assert [a["nome"] for a in (await dentro.get("/painel/api/agentes", params={"ativo": False})).json()] == ["Ana"]
    assert [a["nome"] for a in (await dentro.get("/painel/api/agentes", params={"ativo": True})).json()] == ["Caio"]


async def test_empresa_que_nao_existe_no_filtro_e_404(dentro: httpx.AsyncClient):
    resposta = await dentro.get("/painel/api/agentes", params={"cliente_id": str(uuid.uuid4())})
    assert resposta.status_code == 404


async def test_lista_nao_devolve_credencial_em_claro(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    """A lista não carrega o token do webhook: ele só sai na ficha, que é onde se copia o endereço."""
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    corpo = (await dentro.get("/painel/api/agentes")).text
    assert agente["token"] not in corpo
    assert CONEXAO_EXEMPLO.get("token_admin", "nao-existe") not in corpo
    assert "****" in corpo, "o segredo do bot sai mascarado, como no menu"


# Criação


async def test_agente_criado_pelo_painel_aparece_no_terminal(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    """O critério de aceite da etapa 3: painel e terminal são a mesma operação."""
    empresa = await cria_empresa(dentro, "Loja Exemplo")
    resposta = await dentro.post(
        f"/painel/api/empresas/{empresa['id']}/agentes",
        json={"nome": "Ana", "canal": "chatwoot", "conexao": CONEXAO_EXEMPLO},
    )
    assert resposta.status_code == 201, resposta.text
    criado = resposta.json()
    assert criado["nome"] == "Ana"
    assert criado["empresa"] == "Loja Exemplo"
    assert criado["ativo"] is True

    do_terminal = (await http.get("/admin/agentes", headers=ADMIN)).json()
    assert [a["id"] for a in do_terminal] == [criado["id"]]


async def test_agente_nasce_cru_como_no_terminal(dentro: httpx.AsyncClient, canal):
    """Sem ferramenta marcada e sem emoji: é a decisão da v0.8.11, e vale nos dois lugares."""
    empresa = await cria_empresa(dentro, "Loja Exemplo")
    criado = (
        await dentro.post(
            f"/painel/api/empresas/{empresa['id']}/agentes",
            json={"nome": "Ana", "canal": "nativo"},
        )
    ).json()
    assert criado["ferramentas"] == []
    assert criado["emojis"] == "nenhum"


async def test_canal_que_nao_existe_e_422(dentro: httpx.AsyncClient):
    empresa = await cria_empresa(dentro, "Loja Exemplo")
    resposta = await dentro.post(
        f"/painel/api/empresas/{empresa['id']}/agentes",
        json={"nome": "Ana", "canal": "telepatia"},
    )
    assert resposta.status_code == 422


async def test_empresa_que_nao_existe_na_criacao_e_404(dentro: httpx.AsyncClient):
    resposta = await dentro.post(
        f"/painel/api/empresas/{uuid.uuid4()}/agentes", json={"nome": "Ana", "canal": "nativo"}
    )
    assert resposta.status_code == 404


# Ficha e edição


async def test_ficha_abre_pelo_id_sem_a_empresa_na_url(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    ficha = (await dentro.get(f"/painel/api/agentes/{agente['id']}")).json()
    assert ficha["nome"] == "Ana"
    assert ficha["empresa"] == "Loja Exemplo"
    assert ficha["url_webhook"].endswith(agente["token"])


async def test_agente_que_nao_existe_e_404(dentro: httpx.AsyncClient):
    assert (await dentro.get(f"/painel/api/agentes/{uuid.uuid4()}")).status_code == 404


async def test_edicao_muda_so_o_que_veio(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    antes = (await dentro.get(f"/painel/api/agentes/{agente['id']}")).json()

    depois = (
        await dentro.patch(
            f"/painel/api/agentes/{agente['id']}",
            json={"emojis": "muito", "max_mensagens_por_resposta": 2},
        )
    ).json()
    assert depois["emojis"] == "muito"
    assert depois["max_mensagens_por_resposta"] == 2
    assert depois["buffer_segundos"] == antes["buffer_segundos"]
    assert depois["nome"] == "Ana"


async def test_desligar_e_religar_o_agente(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    assert (await dentro.patch(f"/painel/api/agentes/{agente['id']}", json={"ativo": False})).json()["ativo"] is False
    assert (await dentro.patch(f"/painel/api/agentes/{agente['id']}", json={"ativo": True})).json()["ativo"] is True


async def test_campo_desconhecido_na_edicao_e_recusado(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    resposta = await dentro.patch(
        f"/painel/api/agentes/{agente['id']}", json={"cliente_id": str(uuid.uuid4())}
    )
    assert resposta.status_code == 422, "cliente_id nunca vem do corpo"


async def test_edicao_sem_csrf_nao_passa(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    resposta = await dentro.patch(
        f"/painel/api/agentes/{agente['id']}",
        json={"emojis": "muito"},
        headers={"X-Painel-CSRF": "inventado"},
    )
    assert resposta.status_code == 403


# Remoção


async def test_remover_exige_o_nome_digitado(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    errado = await dentro.request(
        "DELETE", f"/painel/api/agentes/{agente['id']}", json={"confirmacao": "Bia"}
    )
    assert errado.status_code == 422
    assert (await dentro.get(f"/painel/api/agentes/{agente['id']}")).status_code == 200

    certo = await dentro.request(
        "DELETE", f"/painel/api/agentes/{agente['id']}", json={"confirmacao": "Ana"}
    )
    assert certo.status_code == 200
    assert certo.json()["removido"] is True
    assert (await dentro.get(f"/painel/api/agentes/{agente['id']}")).status_code == 404


# Catálogos


async def test_catalogo_de_ferramentas_traz_a_instrucao_de_uso(dentro: httpx.AsyncClient):
    catalogo = (await dentro.get("/painel/api/ferramentas")).json()
    assert catalogo, "a instalação tem pelo menos a calculadora e a busca"
    assert all({"nome", "rotulo", "descricao", "padrao"} == set(f) for f in catalogo)


async def test_modelos_lista_os_provedores_por_funcao(dentro: httpx.AsyncClient):
    modelos = (await dentro.get("/painel/api/modelos")).json()
    assert "openai" in modelos["provedores"]
    assert "anthropic" not in modelos["provedores_transcricao"], "transcrição não tem Anthropic"
    assert [f["campo"] for f in modelos["funcoes"]][0] == "modelo_conversa"


async def test_canais_saem_do_registro(dentro: httpx.AsyncClient):
    canais = {c["nome"]: c for c in (await dentro.get("/painel/api/canais")).json()}
    assert set(canais) == {"chatwoot", "nativo", "waha", "whatsapp"}
    assert canais["nativo"]["externo"] is False
    assert canais["chatwoot"]["externo"] is True


async def test_catalogo_sem_sessao_nao_sai(painel: httpx.AsyncClient):
    assert (await painel.get("/painel/api/ferramentas")).status_code == 401
    assert (await painel.get("/painel/api/modelos")).status_code == 401


# Trabalho: perfil e prompt


async def test_prompt_novo_e_a_linha_do_modelo(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    prompt = (await dentro.get(f"/painel/api/agentes/{agente['id']}/prompt")).json()
    assert "Ana" in prompt["texto"] and "Loja Exemplo" in prompt["texto"]
    assert prompt["perfil"] == {}
    assert prompt["arquivo"].endswith("persona.md")


async def test_perfil_preenchido_reescreve_o_persona(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    """O critério da aba Trabalho: preencho os campos e o texto do prompt muda no disco."""
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    resposta = await dentro.put(
        f"/painel/api/agentes/{agente['id']}/perfil",
        json={
            "funcao": "vendas",
            "publico": "quem procura tênis de corrida",
            "site": "https://exemplo.com.br",
            "sobre_empresa": "Loja de artigos esportivos desde 2015.",
            "assina_nome": True,
        },
    )
    assert resposta.status_code == 200, resposta.text
    texto = resposta.json()["prompt"]
    assert "ajuda quem está decidindo a comprar" in texto
    assert "quem procura tênis de corrida" in texto
    assert "desde 2015" in texto
    assert "Assine as respostas com o seu nome, Ana." in texto

    guardado = (await dentro.get(f"/painel/api/agentes/{agente['id']}/prompt")).json()
    assert guardado["texto"] == texto
    assert guardado["perfil"]["funcao"] == "vendas"


async def test_funcao_desconhecida_e_recusada(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    resposta = await dentro.put(
        f"/painel/api/agentes/{agente['id']}/perfil", json={"funcao": "telemarketing"}
    )
    assert resposta.status_code == 422


async def test_prompt_editado_a_mao_fica(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await dentro.put(
        f"/painel/api/agentes/{agente['id']}/prompt", json={"texto": "Escrito à mão pelo operador."}
    )
    assert (await dentro.get(f"/painel/api/agentes/{agente['id']}/prompt")).json()[
        "texto"
    ] == "Escrito à mão pelo operador."


async def test_perfil_de_uma_empresa_nao_vaza_para_a_outra(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal
):
    """Achado A05 da auditoria: o perfil é por agente, e o prompt de um não entra no do outro."""
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    caio = await cria_cliente_e_agente(http, "Clínica Exemplo", "Caio")
    await dentro.put(
        f"/painel/api/agentes/{ana['id']}/perfil",
        json={"funcao": "vendas", "sobre_empresa": "Segredo da Loja Exemplo."},
    )
    do_caio = (await dentro.get(f"/painel/api/agentes/{caio['id']}/prompt")).json()
    assert "Segredo da Loja Exemplo" not in do_caio["texto"]
    assert do_caio["perfil"] == {}


# Conversa de teste


async def test_conversa_de_teste_manda_e_le(
    dentro: httpx.AsyncClient, http: httpx.AsyncClient, canal, fila
):
    """O mesmo canal nativo do `asimov conversar`: o agente responde de verdade."""
    empresa = await cria_empresa(dentro, "Loja Exemplo")
    agente = (
        await dentro.post(
            f"/painel/api/empresas/{empresa['id']}/agentes",
            json={"nome": "Ana", "canal": "nativo"},
        )
    ).json()

    enviada = await dentro.post(
        f"/painel/api/agentes/{agente['id']}/teste", json={"texto": "oi, tudo bem?"}
    )
    assert enviada.status_code == 200, enviada.text
    conversa = enviada.json()["conversa"]
    assert enviada.json()["agendada"] is True

    leitura = await dentro.get(f"/painel/api/agentes/{agente['id']}/teste/{conversa}")
    assert leitura.status_code == 200
    assert "mensagens" in leitura.json()


async def test_teste_de_agente_que_nao_existe_e_404(dentro: httpx.AsyncClient, fila):
    resposta = await dentro.post(f"/painel/api/agentes/{uuid.uuid4()}/teste", json={"texto": "oi"})
    assert resposta.status_code == 404


async def test_teste_sem_sessao_nao_passa(painel: httpx.AsyncClient):
    resposta = await painel.post(f"/painel/api/agentes/{uuid.uuid4()}/teste", json={"texto": "oi"})
    assert resposta.status_code == 401


# Melhorar texto com a IA


async def test_melhorar_texto_devolve_a_versao_da_ia(dentro, monkeypatch):
    """O botão de estrelinha do onboarding. O texto do operador vai como material, não como ordem."""
    from pydantic_ai.models.function import FunctionModel
    from pydantic_ai.messages import ModelResponse, TextPart

    recebido: dict[str, str] = {}

    def responde(mensagens, info):
        recebido["prompt"] = str(mensagens[-1].parts[-1].content)
        return ModelResponse(parts=[TextPart("A Loja Exemplo vende tênis de corrida.")])

    monkeypatch.setattr("app.ia.provedores.construir_modelo", lambda nome: FunctionModel(responde))

    resposta = await dentro.post(
        "/painel/api/texto/melhorar",
        json={"texto": "vendemos tenis pra corrida", "empresa": "Loja Exemplo"},
    )
    assert resposta.status_code == 200, resposta.text
    assert resposta.json()["texto"] == "A Loja Exemplo vende tênis de corrida."
    # O que o operador escreveu chega delimitado, para não virar instrução para o modelo.
    assert "<material>" in recebido["prompt"]
    assert "vendemos tenis pra corrida" in recebido["prompt"]


async def test_melhorar_texto_sem_chave_de_ia_diz_onde_resolver(dentro, monkeypatch):
    from app.ia import chaves

    monkeypatch.setattr(chaves, "chave_do_provedor", lambda provedor, cfg=None: "")
    resposta = await dentro.post("/painel/api/texto/melhorar", json={"texto": "oi"})
    assert resposta.status_code == 422
    assert "Configurações" in resposta.json()["detail"]


async def test_melhorar_texto_com_provedor_fora_do_ar_nao_derruba_o_onboarding(dentro, monkeypatch):
    def explode(nome):
        raise RuntimeError("provedor fora do ar")

    monkeypatch.setattr("app.ia.provedores.construir_modelo", explode)
    resposta = await dentro.post("/painel/api/texto/melhorar", json={"texto": "oi"})
    assert resposta.status_code == 502
    assert "tente de novo" in resposta.json()["detail"]
