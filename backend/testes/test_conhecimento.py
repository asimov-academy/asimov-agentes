"""Base de conhecimento: ingestão, busca e isolamento.

O que estes testes seguram:

- a busca de um agente nunca devolve trecho de outro agente nem de outro cliente;
- documento removido some da busca no mesmo instante;
- o mesmo material duas vezes no mesmo agente é recusado, e no outro agente não;
- material pronto liga a ferramenta de busca sozinho, senão o operador sobe a tabela de preços e o
  agente responde que não sabe;
- arquivo sem texto e formato que não lemos viram erro com motivo, não exceção.

Nenhum teste chama provedor de embeddings: `gerar` vira um vetor por palavra, o que mantém a
distância do cosseno com significado (texto parecido, vetor próximo).
"""

import hashlib
import uuid
from typing import Any

import httpx
import pytest

from app.conhecimento import embeddings, repo, servico
from app.conhecimento.modelos import DIMENSAO
from testes.conftest import ADMIN, cria_cliente_e_agente

def pdf_com_texto(texto: str) -> bytes:
    """Um PDF de uma página, montado à mão: o teste não pode depender de um arquivo no repositório."""
    fluxo = f"BT /F1 12 Tf 20 100 Td ({texto}) Tj ET".encode()
    objetos = [
        b"<</Type/Catalog/Pages 2 0 R>>",
        b"<</Type/Pages/Kids[3 0 R]/Count 1>>",
        b"<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>",
        b"<</Length " + str(len(fluxo)).encode() + b">>stream\n" + fluxo + b"\nendstream",
        b"<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>",
    ]
    saida = bytearray(b"%PDF-1.4\n")
    posicoes = []
    for numero, corpo in enumerate(objetos, start=1):
        posicoes.append(len(saida))
        saida += str(numero).encode() + b" 0 obj" + corpo + b"endobj\n"
    inicio_xref = len(saida)
    saida += b"xref\n0 " + str(len(objetos) + 1).encode() + b"\n0000000000 65535 f \n"
    for posicao in posicoes:
        saida += f"{posicao:010d} 00000 n \n".encode()
    saida += b"trailer<</Size " + str(len(objetos) + 1).encode() + b"/Root 1 0 R>>\nstartxref\n"
    saida += str(inicio_xref).encode() + b"\n%%EOF\n"
    return bytes(saida)


def vetor_de(texto: str) -> list[float]:
    """Saco de palavras normalizado: sem rede, e com cosseno que ainda quer dizer alguma coisa."""
    vetor = [0.0] * DIMENSAO
    for palavra in texto.lower().split():
        indice = int(hashlib.sha256(palavra.encode()).hexdigest(), 16) % DIMENSAO
        vetor[indice] += 1.0
    tamanho = sum(v * v for v in vetor) ** 0.5 or 1.0
    return [v / tamanho for v in vetor]


@pytest.fixture(autouse=True)
def sem_provedor(monkeypatch: pytest.MonkeyPatch) -> None:
    """Sem rede e sem worker: a ingestão roda dentro da requisição, como na instalação sem fila."""
    from app.main import app

    async def gerar(textos: list[str], cfg: Any = None, **kwargs: Any) -> list[list[float]]:
        return [vetor_de(t) for t in textos]

    monkeypatch.setattr(embeddings, "gerar", gerar)
    monkeypatch.setattr(servico.embeddings, "gerar", gerar)
    # Outro teste pode ter deixado uma fila falsa no app: com ela, o documento ficaria
    # "processando" para sempre, porque ninguém roda o job aqui.
    monkeypatch.delattr(app.state, "fila", raising=False)


async def envia_texto(http: httpx.AsyncClient, agente: dict, texto: str, titulo: str = "") -> dict:
    resposta = await http.post(
        f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}/documentos/texto",
        json={"texto": texto, "titulo": titulo},
        headers=ADMIN,
    )
    assert resposta.status_code == 201, resposta.text
    return resposta.json()


async def test_texto_vira_trecho_e_a_busca_acha(http, canal, sessao) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    documento = await envia_texto(http, agente, "A camiseta preta custa 90 reais e sai em dois dias.")
    assert documento["status"] == "pronto" and documento["total_trechos"] == 1

    async with sessao() as s:
        achados = await servico.buscar(
            s, uuid.UUID(agente["cliente_id"]), uuid.UUID(agente["id"]), "quanto custa a camiseta"
        )
    assert achados and "90 reais" in achados[0]["texto"]


async def test_busca_de_um_agente_nunca_devolve_material_de_outro(http, canal, sessao) -> None:
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    bia = await cria_cliente_e_agente(http, "Padaria Pão Quente", "Bia")
    await envia_texto(http, ana, "A camiseta preta custa 90 reais.")
    await envia_texto(http, bia, "O pão de queijo custa 5 reais.")

    async with sessao() as s:
        da_ana = await servico.buscar(
            s, uuid.UUID(ana["cliente_id"]), uuid.UUID(ana["id"]), "quanto custa o pão de queijo"
        )
        da_bia = await servico.buscar(
            s, uuid.UUID(bia["cliente_id"]), uuid.UUID(bia["id"]), "quanto custa a camiseta"
        )
    assert all("pão de queijo" not in a["texto"] for a in da_ana)
    assert all("camiseta" not in a["texto"] for a in da_bia)


async def test_dois_agentes_da_mesma_empresa_nao_compartilham_base(http, canal, sessao) -> None:
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    outro = (
        await http.post(
            f"/admin/clientes/{ana['cliente_id']}/agentes",
            json={"nome": "Beto", "canal": "nativo"},
            headers=ADMIN,
        )
    ).json()
    await envia_texto(http, ana, "A camiseta preta custa 90 reais.")

    async with sessao() as s:
        do_beto = await servico.buscar(
            s, uuid.UUID(ana["cliente_id"]), uuid.UUID(outro["id"]), "camiseta"
        )
    assert do_beto == []


async def test_material_removido_some_da_busca(http, canal, sessao) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    documento = await envia_texto(http, agente, "A camiseta preta custa 90 reais.")

    caminho = f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}/documentos"
    assert (await http.delete(f"{caminho}/{documento['id']}", headers=ADMIN)).status_code == 200

    async with sessao() as s:
        assert await servico.buscar(
            s, uuid.UUID(agente["cliente_id"]), uuid.UUID(agente["id"]), "camiseta"
        ) == []
    assert (await http.get(caminho, headers=ADMIN)).json() == []


async def test_mesmo_material_duas_vezes_no_mesmo_agente_e_recusado(http, canal) -> None:
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    bia = await cria_cliente_e_agente(http, "Padaria Pão Quente", "Bia")
    await envia_texto(http, ana, "A camiseta preta custa 90 reais.")

    repetido = await http.post(
        f"/admin/clientes/{ana['cliente_id']}/agentes/{ana['id']}/documentos/texto",
        json={"texto": "A camiseta preta custa 90 reais."},
        headers=ADMIN,
    )
    assert repetido.status_code == 409
    # No outro agente, o mesmo material entra: a base é de cada agente.
    await envia_texto(http, bia, "A camiseta preta custa 90 reais.")


async def test_material_pronto_liga_a_ferramenta_de_busca(http, canal) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    assert agente["ferramentas"] == []
    await envia_texto(http, agente, "A camiseta preta custa 90 reais.")

    ficha = await http.get(
        f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}", headers=ADMIN
    )
    assert "base_conhecimento" in ficha.json()["ferramentas"]


async def test_arquivo_pdf_vira_base(http, canal) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    resposta = await http.post(
        f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}/documentos",
        files={"arquivo": ("precos.pdf", pdf_com_texto("camiseta preta 90 reais"), "application/pdf")},
        headers=ADMIN,
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["status"] == "pronto"
    assert resposta.json()["total_trechos"] == 1


async def test_formato_que_nao_lemos_e_recusado_na_hora(http, canal) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    resposta = await http.post(
        f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}/documentos",
        files={"arquivo": ("foto.png", b"\x89PNG\r\n", "image/png")},
        headers=ADMIN,
    )
    assert resposta.status_code == 422
    assert "PDF" in resposta.json()["detail"]


async def test_arquivo_sem_texto_vira_erro_com_motivo(http, canal) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    resposta = await http.post(
        f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}/documentos",
        files={"arquivo": ("vazio.txt", b"   \n  ", "text/plain")},
        headers=ADMIN,
    )
    assert resposta.status_code == 201, resposta.text
    assert resposta.json()["status"] == "erro"
    assert "texto" in resposta.json()["erro"]


async def test_sem_chave_de_embeddings_o_material_diz_o_que_falta(http, canal, monkeypatch) -> None:
    async def sem_chave(textos: list[str], cfg: Any = None, **kwargs: Any) -> list[list[float]]:
        raise embeddings.SemEmbeddings(
            "a base de conhecimento precisa da chave da OpenAI ou do Gemini nesta instalação"
        )

    monkeypatch.setattr(servico.embeddings, "gerar", sem_chave)
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    documento = await envia_texto(http, agente, "A camiseta preta custa 90 reais.")
    assert documento["status"] == "erro"
    assert "OpenAI" in documento["erro"]


async def test_agente_de_outro_cliente_na_url_nao_acha_o_material(http, canal) -> None:
    ana = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    bia = await cria_cliente_e_agente(http, "Padaria Pão Quente", "Bia")
    documento = await envia_texto(http, ana, "A camiseta preta custa 90 reais.")

    # O cliente da URL é conferido no banco: id de outro cliente não alcança o documento.
    fora = await http.delete(
        f"/admin/clientes/{bia['cliente_id']}/agentes/{ana['id']}/documentos/{documento['id']}",
        headers=ADMIN,
    )
    assert fora.status_code == 404
    lista = await http.get(
        f"/admin/clientes/{bia['cliente_id']}/agentes/{bia['id']}/documentos", headers=ADMIN
    )
    assert lista.json() == []


async def test_busca_vazia_quando_o_agente_nao_tem_base(http, canal, sessao) -> None:
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    async with sessao() as s:
        assert await servico.buscar(
            s, uuid.UUID(agente["cliente_id"]), uuid.UUID(agente["id"]), "qualquer coisa"
        ) == []
        assert await repo.listar(s, uuid.UUID(agente["cliente_id"]), uuid.UUID(agente["id"])) == []


async def test_com_worker_no_ar_a_requisicao_so_enfileira(http, canal, fila, sessao) -> None:
    """Na instalação de verdade quem ingere é o worker: a rota grava `processando` e enfileira."""
    from app.worker import ingerir_documento

    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    resposta = await http.post(
        f"/admin/clientes/{agente['cliente_id']}/agentes/{agente['id']}/documentos/texto",
        json={"texto": "A camiseta preta custa 90 reais."},
        headers=ADMIN,
    )
    assert resposta.status_code == 201
    assert resposta.json()["status"] == "processando"
    nome, *argumentos = fila.jobs[-1]
    assert nome == "ingerir_documento"

    assert await ingerir_documento({}, *argumentos) == "pronto"
    async with sessao() as s:
        achados = await servico.buscar(
            s, uuid.UUID(agente["cliente_id"]), uuid.UUID(agente["id"]), "camiseta"
        )
    assert achados
