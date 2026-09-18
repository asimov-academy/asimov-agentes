"""Painel do operador: senha, código de primeiro acesso, sessão e o que ele deixa ver.

O que estes testes seguram, além do caminho feliz: ninguém cria a conta sem o código do terminal,
ninguém cria uma segunda conta, e `/admin` continua exigindo a chave mesmo com o painel no ar.
"""

import uuid
from unittest.mock import AsyncMock

import httpx
import pytest

from app.painel import servico
from testes.conftest import ADMIN, cria_cliente_e_agente, limpa_o_redis_do_painel

SENHA = "senha-boa-do-operador"


async def codigo_novo() -> str:
    codigo = servico.novo_codigo()
    await servico.guarda_codigo(codigo)
    return codigo


async def entra(painel: httpx.AsyncClient) -> None:
    resposta = await painel.post(
        "/painel/primeiro-acesso",
        data={"codigo": await codigo_novo(), "senha": SENHA, "senha2": SENHA},
    )
    assert resposta.status_code == 303, resposta.text


# Senha


def test_senha_cifrada_confere_e_nao_repete():
    guardado = servico.cifra_senha(SENHA)
    assert guardado.startswith("scrypt$")
    assert SENHA not in guardado
    assert servico.confere_senha(SENHA, guardado)
    assert not servico.confere_senha("outra-coisa-qualquer", guardado)
    # Sal aleatório: a mesma senha nunca gera o mesmo registro.
    assert servico.cifra_senha(SENHA) != guardado


def test_senha_curta_e_recusada():
    assert servico.senha_fraca("curta")
    assert servico.senha_fraca("123456789012")
    assert servico.senha_fraca(SENHA) == ""


def test_hash_estragado_nao_deixa_entrar():
    assert not servico.confere_senha(SENHA, "coisa-que-nao-e-hash")
    assert not servico.confere_senha(SENHA, "md5$1$2$3$4$5")


# Primeiro acesso


async def test_sem_conta_a_raiz_manda_criar_o_acesso(painel: httpx.AsyncClient):
    resposta = await painel.get("/painel/")
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/painel/primeiro-acesso"


async def test_primeiro_acesso_exige_o_codigo_do_terminal(painel: httpx.AsyncClient):
    resposta = await painel.post(
        "/painel/primeiro-acesso", data={"codigo": "XXXX-XXXX", "senha": SENHA, "senha2": SENHA}
    )
    assert resposta.status_code == 200
    assert "Código inválido" in resposta.text
    # Nada foi criado: a raiz continua mandando para o primeiro acesso.
    assert (await painel.get("/painel/")).headers["location"] == "/painel/primeiro-acesso"


async def test_codigo_vale_uma_vez_so(painel: httpx.AsyncClient):
    codigo = await codigo_novo()
    assert await servico.gasta_codigo(codigo)
    assert not await servico.gasta_codigo(codigo)


async def test_codigo_aceita_minusculas_e_espaco(painel: httpx.AsyncClient):
    codigo = await codigo_novo()
    assert await servico.gasta_codigo(f"  {codigo.lower()} ")


async def test_senhas_diferentes_nao_criam_conta(painel: httpx.AsyncClient):
    resposta = await painel.post(
        "/painel/primeiro-acesso",
        data={"codigo": await codigo_novo(), "senha": SENHA, "senha2": SENHA + "!"},
    )
    assert "não são iguais" in resposta.text


async def test_primeiro_acesso_cria_a_conta_e_ja_entra(painel: httpx.AsyncClient):
    await entra(painel)
    assert painel.cookies.get("asimov_painel")
    assert (await painel.get("/painel/api/eu")).status_code == 200


async def test_segunda_conta_nao_e_criada(painel: httpx.AsyncClient):
    await entra(painel)
    resposta = await painel.post(
        "/painel/primeiro-acesso",
        data={"codigo": await codigo_novo(), "senha": "outra-senha-comprida", "senha2": "outra-senha-comprida"},
    )
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/painel/entrar"


# Entrar e sair


async def test_senha_errada_nao_entra(painel: httpx.AsyncClient):
    await entra(painel)
    painel.cookies.clear()
    resposta = await painel.post("/painel/entrar", data={"senha": "chute"})
    assert resposta.status_code == 200
    assert "Senha incorreta" in resposta.text
    assert not painel.cookies.get("asimov_painel")


async def test_senha_certa_entra(painel: httpx.AsyncClient):
    await entra(painel)
    painel.cookies.clear()
    resposta = await painel.post("/painel/entrar", data={"senha": SENHA})
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/painel/app"
    assert painel.cookies.get("asimov_painel")


async def test_cookie_da_sessao_e_fechado(painel: httpx.AsyncClient):
    await entra(painel)
    painel.cookies.clear()
    resposta = await painel.post("/painel/entrar", data={"senha": SENHA})
    bruto = resposta.headers["set-cookie"].lower()
    assert "httponly" in bruto and "secure" in bruto and "samesite=strict" in bruto


async def test_sair_derruba_a_sessao(painel: httpx.AsyncClient):
    await entra(painel)
    await painel.post("/painel/sair")
    assert (await painel.get("/painel/inicio")).status_code == 401


async def test_erros_seguidos_seguram_a_porta(painel: httpx.AsyncClient):
    await entra(painel)
    painel.cookies.clear()
    for _ in range(servico.ERROS_ANTES_DA_ESPERA):
        await painel.post("/painel/entrar", data={"senha": "chute"})
    resposta = await painel.post("/painel/entrar", data={"senha": SENHA})
    assert "Espere 15 minutos" in resposta.text


# O que o painel mostra


async def test_painel_fechado_para_quem_nao_entrou(painel: httpx.AsyncClient):
    await entra(painel)
    painel.cookies.clear()
    for caminho in ("/painel/api/eu", "/painel/api/agentes", "/painel/api/visao-geral"):
        assert (await painel.get(caminho)).status_code == 401


async def test_as_telas_antigas_levam_ao_painel_novo(painel: httpx.AsyncClient):
    """`inicio` e `agentes` eram o painel em Jinja2, que o front substituiu. Viraram desvio."""
    await entra(painel)
    for caminho in ("/painel/inicio", "/painel/agentes"):
        resposta = await painel.get(caminho)
        assert resposta.status_code == 303
        assert resposta.headers["location"] == "/painel/app"


async def test_agentes_filtra_por_empresa(painel: httpx.AsyncClient, http: httpx.AsyncClient, canal):
    uma = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await cria_cliente_e_agente(http, "Clínica Exemplo", "Caio")
    await entra(painel)

    todas = (await painel.get("/painel/api/agentes")).text
    assert "Ana" in todas and "Caio" in todas

    so_uma = (await painel.get(f"/painel/api/agentes?cliente_id={uma['cliente_id']}")).text
    assert "Ana" in so_uma and "Caio" not in so_uma


async def test_painel_nao_mostra_credencial(painel: httpx.AsyncClient, http: httpx.AsyncClient, canal):
    await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await entra(painel)
    for pagina in (
        (await painel.get("/painel/api/agentes")).text,
        (await painel.get("/painel/api/visao-geral")).text,
    ):
        assert "chave-admin-de-teste" not in pagina
        assert "token_webhook" not in pagina


async def test_admin_continua_exigindo_a_chave(painel: httpx.AsyncClient):
    """O painel autentica por sessão e não vira porta para o /admin sem chave."""
    await entra(painel)
    assert (await painel.get("/admin/agentes")).status_code == 401
    assert (await painel.get("/admin/clientes")).status_code == 401
    assert (await painel.get("/admin/agentes", headers=ADMIN)).status_code == 200


# O que o setup usa


async def test_setup_ve_o_estado_do_painel(http: httpx.AsyncClient):
    estado = (await http.get("/admin/painel", headers=ADMIN)).json()
    assert estado["ativo"] is True
    assert estado["endereco"] == "https://app.teste.local/painel"
    assert estado["tem_operador"] is False


async def test_setup_gera_o_codigo_que_o_navegador_gasta(
    http: httpx.AsyncClient, painel: httpx.AsyncClient
):
    gerado = (await http.post("/admin/painel/codigo", headers=ADMIN)).json()
    assert gerado["minutos"] == 15
    resposta = await painel.post(
        "/painel/primeiro-acesso",
        data={"codigo": gerado["codigo"], "senha": SENHA, "senha2": SENHA},
    )
    assert resposta.status_code == 303
    assert (await http.get("/admin/painel", headers=ADMIN)).json()["tem_operador"] is True


async def test_esquecer_operador_derruba_a_sessao(
    http: httpx.AsyncClient, painel: httpx.AsyncClient
):
    await entra(painel)
    assert (await painel.get("/painel/api/eu")).status_code == 200
    assert (await http.delete("/admin/painel/operador", headers=ADMIN)).status_code == 204
    assert (await painel.get("/painel/api/eu")).status_code == 401
    assert (await painel.get("/painel/")).headers["location"] == "/painel/primeiro-acesso"


async def test_rotas_do_setup_exigem_a_chave(http: httpx.AsyncClient):
    assert (await http.get("/admin/painel")).status_code == 401
    assert (await http.post("/admin/painel/codigo")).status_code == 401
    assert (await http.delete("/admin/painel/operador")).status_code == 401


# Origem dos formulários (CSRF)


async def test_origem_parecida_nao_passa(painel: httpx.AsyncClient):
    """`painel.teste.outracoisa.com` começa com o endereço certo e não é ele."""
    await entra(painel)
    painel.cookies.clear()
    for origem in (
        "https://painel.teste.outracoisa.com",
        "https://painel.teste.evil",
        "https://outro.site",
        "http://painel.teste@evil.com",
    ):
        resposta = await painel.post(
            "/painel/entrar", data={"senha": SENHA}, headers={"Origin": origem}
        )
        assert resposta.status_code == 403, f"{origem} passou"


async def test_origem_certa_passa(painel: httpx.AsyncClient):
    await entra(painel)
    painel.cookies.clear()
    for origem in ("https://painel.teste", "https://painel.teste/painel/entrar", "https://app.teste.local"):
        resposta = await painel.post(
            "/painel/entrar", data={"senha": SENHA}, headers={"Origin": origem}
        )
        assert resposta.status_code == 303, f"{origem} foi barrada"


async def test_referer_de_outro_site_nao_cria_conta(painel: httpx.AsyncClient):
    resposta = await painel.post(
        "/painel/primeiro-acesso",
        data={"codigo": await codigo_novo(), "senha": SENHA, "senha2": SENHA},
        headers={"Referer": "https://site-qualquer.exemplo/pagina"},
    )
    assert resposta.status_code == 403
    assert (await painel.get("/painel/")).headers["location"] == "/painel/primeiro-acesso"


# Falhas na tela


def test_resumo_da_falha_corta_e_nao_despeja_o_json():
    from app.painel.rotas import LIMITE_RESUMO_DA_FALHA, resumo_da_falha

    assert resumo_da_falha(None) == ""
    assert resumo_da_falha({}) == ""
    assert resumo_da_falha({"erro": "  tempo   esgotado\nno provedor "}) == "tempo esgotado no provedor"
    # Campo que não é `erro` nem `problemas` não vai para a tela: pode ser resposta crua de API.
    assert resumo_da_falha({"corpo": {"api_key": "sk-de-verdade"}}) == ""
    assert len(resumo_da_falha({"erro": "x" * 500})) == LIMITE_RESUMO_DA_FALHA


async def test_tela_nao_mostra_o_detalhe_cru_da_falha(
    painel: httpx.AsyncClient, http: httpx.AsyncClient, canal, sessao
):
    from app.consumo import repo as consumo_repo

    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await consumo_repo.registra_falha(
        tipo="turno_modelo_falhou",
        detalhe={"erro": "tempo esgotado", "corpo": {"api_key": "sk-nunca-na-tela"}},
        cliente_id=uuid.UUID(agente["cliente_id"]),
        agente_id=uuid.UUID(agente["id"]),
    )
    await entra(painel)
    pagina = (await painel.get("/painel/api/visao-geral")).text
    assert "tempo esgotado" in pagina
    assert "sk-nunca-na-tela" not in pagina
    assert "api_key" not in pagina


# Uma conta só, e código que sobrevive a falha na criação


async def test_duas_criacoes_ao_mesmo_tempo_deixam_uma_conta(painel: httpx.AsyncClient):
    """A corrida não é hipotética: dois códigos válidos e dois navegadores bastam."""
    import asyncio

    codigos = [await codigo_novo(), await codigo_novo()]
    respostas = await asyncio.gather(*[
        painel.post(
            "/painel/primeiro-acesso",
            data={"codigo": c, "senha": SENHA, "senha2": SENHA},
        )
        for c in codigos
    ])
    assert all(r.status_code == 303 for r in respostas)
    # Uma virou sessão, a outra foi mandada para o login. Nunca duas contas.
    assert sorted(r.headers["location"] for r in respostas) == ["/painel/app", "/painel/entrar"]


async def test_codigo_so_e_gasto_com_a_conta_criada(painel: httpx.AsyncClient, monkeypatch):
    from app.painel import repo as painel_repo

    codigo = await codigo_novo()
    monkeypatch.setattr(
        painel_repo, "cria", AsyncMock(side_effect=RuntimeError("banco fora do ar"))
    )
    with pytest.raises(RuntimeError):
        await painel.post(
            "/painel/primeiro-acesso", data={"codigo": codigo, "senha": SENHA, "senha2": SENHA}
        )
    monkeypatch.undo()

    # O código continua valendo: a criação não chegou a acontecer.
    resposta = await painel.post(
        "/painel/primeiro-acesso", data={"codigo": codigo, "senha": SENHA, "senha2": SENHA}
    )
    assert resposta.status_code == 303
    assert resposta.headers["location"] == "/painel/app"


async def test_codigo_usado_nao_serve_de_novo(painel: httpx.AsyncClient):
    codigo = await codigo_novo()
    assert (await painel.post(
        "/painel/primeiro-acesso", data={"codigo": codigo, "senha": SENHA, "senha2": SENHA}
    )).status_code == 303
    assert not await servico.codigo_vale(codigo)


async def test_o_banco_recusa_a_segunda_conta(sessao):
    """A garantia é do banco, não da ordem em que as requisições chegaram."""
    from sqlalchemy.exc import IntegrityError

    from app.painel.modelos import UsuarioPainel

    async with sessao() as s:
        s.add(UsuarioPainel(senha=servico.cifra_senha(SENHA)))
        await s.commit()
    with pytest.raises(IntegrityError):
        async with sessao() as s:
            s.add(UsuarioPainel(senha=servico.cifra_senha("outra-senha-comprida")))
            await s.commit()


async def test_situacao_diz_o_que_contou_nos_quatro_estados():
    """O texto do ponto de situação tem um formato só, e nunca a palavra handoff.

    Ele dizia "tudo no ar" no verde e "N handoffs vencidos" no amarelo: dois formatos, e um deles
    com palavra do código. Agora ele sempre diz o que foi contado, e o verde mostra os dois zeros.
    """
    from app.painel.servico import _situacao

    vencido = {"vencido": True}
    falha = {"tipo": "envio_falhou"}

    assert _situacao([], []) == {"cor": "ok", "texto": "0 falhas · 0 paradas"}
    assert _situacao([falha], []) == {"cor": "atencao", "texto": "1 falha · 0 paradas"}
    assert _situacao([], [vencido, vencido]) == {"cor": "atencao", "texto": "0 falhas · 2 paradas"}
    assert _situacao([{"tipo": "canal_fora_do_ar"}], []) == {"cor": "perigo", "texto": "canal fora do ar"}

    for falhas, handoffs in (([], []), ([falha], [vencido])):
        assert "handoff" not in _situacao(falhas, handoffs)["texto"]
