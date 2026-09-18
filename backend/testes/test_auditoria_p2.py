"""Regressões dos achados P2 da auditoria de 2026-09-18 já corrigidos.

Relatório: docs/auditoria-2026-09-18.md. O que continua aberto está em
`testes/auditoria_2026_09_18.py`, com a expectativa do defeito.
"""

from pathlib import Path

import httpx
import pytest
from sqlalchemy import select

from app.consumo.modelos import Falha
from app.conversas.modelos import Mensagem
from app.ia.provedores import ModeloInvalido, valida_modelos
from app.plataforma.publico import pagina
from testes.conftest import ADMIN, cria_cliente_e_agente
from testes.test_whatsapp import cria_agente, manda, meta, payload  # noqa: F401

RAIZ = Path(__file__).resolve().parents[2]


# A07 e A08: envelope da Cloud API


async def test_lote_com_duas_mensagens_grava_as_duas(http, fila, meta, sessao):
    """A Meta junta o que chegou junto; ler só a primeira perdia a segunda em silêncio."""
    agente = await cria_agente(http)
    corpo = payload(texto="Primeira", id_mensagem="wamid.1")
    valor = corpo["entry"][0]["changes"][0]["value"]
    valor["messages"].append({
        "from": valor["messages"][0]["from"],
        "id": "wamid.2",
        "timestamp": "1770000001",
        "type": "text",
        "text": {"body": "Segunda"},
    })

    assert (await manda(http, agente, corpo)).status_code == 200
    async with sessao() as s:
        textos = [m.texto for m in await s.scalars(select(Mensagem).order_by(Mensagem.criado_em))]
    assert textos == ["Primeira", "Segunda"]


async def test_entrega_recusada_vira_falha_visivel(http, fila, meta, sessao):
    """`failed` chega depois do envio aceito; antes sumia junto com o recibo comum."""
    agente = await cria_agente(http)
    corpo = payload(statuses=True)
    corpo["entry"][0]["changes"][0]["value"]["statuses"] = [{
        "id": "wamid.saida1",
        "status": "failed",
        "errors": [{"code": 131047, "title": "Re-engagement message"}],
    }]

    assert (await manda(http, agente, corpo)).status_code == 200
    async with sessao() as s:
        falhas = {f.tipo: f.detalhe for f in await s.scalars(select(Falha))}
    assert "entrega_recusada" in falhas
    assert "131047" in str(falhas["entrega_recusada"])


async def test_recibo_comum_continua_ignorado(http, fila, meta, sessao):
    agente = await cria_agente(http)
    assert (await manda(http, agente, payload(statuses=True))).status_code == 200
    async with sessao() as s:
        assert [f.tipo for f in await s.scalars(select(Falha))] == []


# A11: nada do cadastro vira HTML ativo na página pública


def test_nome_com_tag_nao_vira_script():
    saida = pagina('<script>alert("auditoria")</script>')
    assert "<script>alert" not in saida
    assert "&lt;script&gt;" in saida


def test_aspas_e_acentos_continuam_legiveis():
    saida = pagina('Comércio & Cia "Exemplo"')
    assert "Comércio" in saida
    assert "&amp;" in saida and "&quot;" in saida


# A12: modelo obrigatório não pode ficar vazio


def test_modelo_obrigatorio_vazio_e_recusado():
    for campo in ("modelo_conversa", "modelo_auxiliar", "modelo_visao", "modelo_transcricao"):
        with pytest.raises(ModeloInvalido):
            valida_modelos({campo: ""})
        with pytest.raises(ModeloInvalido):
            valida_modelos({campo: "   "})


def test_fallback_pode_ficar_vazio():
    valida_modelos({"modelo_fallback": ""})
    valida_modelos({"modelo_fallback": None})


async def test_patch_com_modelo_vazio_responde_422(http, canal, fila):
    agente = await cria_cliente_e_agente(http, "Empresa Modelo", "Agente Modelo")
    resposta = await http.patch(
        f'/admin/clientes/{agente["cliente_id"]}/agentes/{agente["id"]}',
        headers=ADMIN,
        json={"modelo_conversa": ""},
    )
    assert resposta.status_code == 422
    atual = await http.get(
        f'/admin/clientes/{agente["cliente_id"]}/agentes/{agente["id"]}', headers=ADMIN
    )
    assert atual.json()["modelo_conversa"]


# A16: publicar também recarrega o servidor web


def test_publicar_recarrega_o_caddy():
    """Caddyfile é montado: sem reload, caminho público novo responde 404 até alguém reiniciar."""
    script = (RAIZ / "deploy" / "publicar.sh").read_text(encoding="utf-8")
    assert "caddy reload" in script


# A17: a limpeza de mídia não para no primeiro lote


async def test_limpeza_apaga_mais_de_um_lote(sessao, monkeypatch, tmp_path):
    """Com 500 por lote e mais de 500 elegíveis, o disco enchia devagar."""
    from app.midia import repo as midia_repo
    from app.midia import servico as midia_servico

    apagados: list[str] = []
    lotes = [
        [_midia_falsa(f"a{i}") for i in range(3)],
        [_midia_falsa(f"b{i}") for i in range(2)],
        [],
    ]

    async def por_lote(*args, **kwargs):
        return lotes.pop(0) if lotes else []

    monkeypatch.setattr(midia_repo, "com_arquivo_antigo", por_lote)
    monkeypatch.setattr(midia_servico.asyncio, "to_thread", _apaga_falso(apagados))

    async with sessao() as s:
        assert await midia_servico.limpa_arquivos_antigos(s) == 5
    assert len(apagados) == 5


def _midia_falsa(nome: str):
    from types import SimpleNamespace

    return SimpleNamespace(id=nome, caminho_arquivo=nome, arquivo_apagado_em=None)


def _apaga_falso(registro: list[str]):
    async def to_thread(funcao, *args, **kwargs):
        registro.append("apagado")
        return None

    return to_thread


# A09: rajada não esconde pergunta do contato


async def test_rajada_maior_que_o_historico_ainda_e_respondida(http, canal, fila, sessao, monkeypatch):
    """41 mensagens antes do turno: as primeiras sumiam do contexto e do marcador."""
    from unittest.mock import AsyncMock

    from app.conversas import turno
    from app.conversas.modelos import Conversa
    from app.ia.agente import ResultadoTurno
    from testes.conftest import envia_webhook, payload_chatwoot

    agente = await cria_cliente_e_agente(http, "Empresa A09", "Agente A09")
    for i in range(41):
        await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=i + 1, conteudo=f"m{i}"))
    async with sessao() as s:
        conversa = await s.scalar(select(Conversa))

    vistas: list[list[str]] = []

    async def modelo(agente_, anteriores, pendentes, *args, **kwargs):
        vistas.append([m.texto for m in pendentes])
        return ResultadoTurno(["Resposta"])

    monkeypatch.setattr(turno, "_roda_com_tentativas", modelo)
    monkeypatch.setattr(turno, "tempos_de_digitacao", lambda textos, *a, **k: [0] * len(textos))
    assert await turno._turno(conversa.cliente_id, conversa.id, AsyncMock(return_value=True)) == "respondido"

    assert vistas and vistas[0][0] == "m0", "a primeira mensagem da rajada precisa chegar ao modelo"
    assert len(vistas[0]) == 41


async def test_mensagens_do_turno_avisa_quando_passa_do_teto(http, canal, fila, sessao):
    from app.conversas import repo as conversas_repo
    from app.conversas.modelos import Conversa
    from testes.conftest import envia_webhook, payload_chatwoot

    agente = await cria_cliente_e_agente(http, "Empresa A09b", "Agente A09b")
    for i in range(5):
        await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=i + 1, conteudo=f"m{i}"))
    async with sessao() as s:
        conversa = await s.scalar(select(Conversa))
        marcador = conversa.criado_em
        mensagens, excedeu = await conversas_repo.mensagens_do_turno(
            s, conversa.cliente_id, conversa.id, marcador, historico=2, teto_pendentes=2
        )
    assert excedeu is True
    assert [m.texto for m in mensagens][-2:] == ["m3", "m4"]


# A18: PDF pesado não pode travar o worker


async def test_pdf_e_lido_fora_do_laco_de_eventos(monkeypatch):
    """Sem thread, ler um PDF grande deixa as outras conversas esperando."""
    import asyncio as _asyncio

    from app.midia import extracao

    threads: list[str] = []
    original = _asyncio.to_thread

    async def registra(funcao, *args, **kwargs):
        threads.append(getattr(funcao, "__name__", "?"))
        return await original(funcao, *args, **kwargs)

    async def sem_modelo(*args, **kwargs):
        return extracao.Extracao(texto="lido pela visão")

    monkeypatch.setattr(extracao.asyncio, "to_thread", registra)
    monkeypatch.setattr(extracao, "_com_modelo", sem_modelo)
    await extracao.ler_documento("openai:gpt-5-mini", _pdf_de_teste(3), "application/pdf")
    assert "_le_pdf" in threads


async def test_pdf_para_no_teto_de_paginas(monkeypatch):
    from app.midia import extracao
    from app.plataforma.config import config

    limite = config().midia_paginas_pdf_visao
    paginas, texto, cortado = extracao._le_pdf(_pdf_de_teste(limite + 5))
    assert paginas == limite + 5
    assert texto.count("Pagina") <= limite, "não pode extrair texto de todas as páginas"
    assert len(cortado) < len(_pdf_de_teste(limite + 5))


def _pdf_de_teste(paginas: int) -> bytes:
    from io import BytesIO

    from pypdf import PdfWriter

    escritor = PdfWriter()
    for _ in range(paginas):
        escritor.add_blank_page(width=200, height=200)
    saida = BytesIO()
    escritor.write(saida)
    return saida.getvalue()


# A20: saúde inclui quem processa o turno


async def test_health_diz_aguardando_antes_do_primeiro_worker(http, fila):
    """Instalação nova: ainda não subiu worker nenhum, e isso não pode derrubar a saúde."""
    corpo = (await http.get("/health")).json()
    assert corpo["worker"] == "aguardando"


async def test_health_reprova_quando_o_worker_some(http, fila):
    from app.plataforma import pulso as worker

    fila.chaves[worker.CHAVE_JA_SUBIU] = "1"
    resposta = await http.get("/health")
    assert resposta.status_code == 503
    assert resposta.json()["worker"] == "parado"


async def test_health_aprova_com_o_pulso_do_worker(http, fila):
    from app.plataforma import pulso as worker

    fila.chaves[worker.CHAVE_JA_SUBIU] = "1"
    fila.chaves[worker.CHAVE_PULSO] = "1770000000"
    resposta = await http.get("/health")
    assert resposta.status_code == 200
    assert resposta.json()["worker"] == "ok"
