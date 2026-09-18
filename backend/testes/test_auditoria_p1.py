"""Regressões dos seis achados P1 da auditoria de 2026-09-18.

Aqui as expectativas são do comportamento correto, ao contrário das sondas em
`auditoria_2026_09_18.py`, que descrevem o defeito. Relatório: docs/auditoria-2026-09-18.md.
"""

from unittest.mock import AsyncMock

import pytest
from sqlalchemy import select

from app.conversas import buffer, turno
from app.conversas.modelos import Conversa, Mensagem
from app.consumo.modelos import Falha
from app.ia.agente import ResultadoTurno
from app.plataforma.config import config
from app.worker import Configuracao
from testes.conftest import ADMIN, cria_cliente_e_agente, envia_webhook, payload_chatwoot
from testes.test_turno import redis  # noqa: F401


async def conversa_com_pendencia(http, sessao, nome="Empresa Auditoria", agente="Agente Auditoria"):
    criado = await cria_cliente_e_agente(http, nome, agente)
    await envia_webhook(http, criado["token"], payload_chatwoot())
    async with sessao() as s:
        return criado, await s.scalar(select(Conversa))


def responde(*mensagens):
    return AsyncMock(return_value=ResultadoTurno(list(mensagens)))


def sem_espera(monkeypatch):
    monkeypatch.setattr(turno, "tempos_de_digitacao", lambda textos, *a, **k: [0] * len(textos))


# A01: reentrega recupera agendamento perdido


async def test_reentrega_recupera_turno_que_a_fila_perdeu(http, canal, fila):
    """Redis fora do ar na primeira entrega: a mensagem fica gravada e sem turno nenhum."""
    agente = await cria_cliente_e_agente(http, "Empresa A01", "Agente A01")
    fila.falhar = True
    assert (await envia_webhook(http, agente["token"], payload_chatwoot())).status_code == 500
    fila.falhar = False

    assert (await envia_webhook(http, agente["token"], payload_chatwoot())).status_code == 200
    assert [j[0] for j in fila.jobs] == ["processar_turno"]


async def test_reentrega_comum_nao_vira_segundo_turno(http, canal, fila):
    """O canal repete bastante: com o turno já agendado, a repetição não agenda outro."""
    agente = await cria_cliente_e_agente(http, "Empresa A01b", "Agente A01b")
    await envia_webhook(http, agente["token"], payload_chatwoot())
    await envia_webhook(http, agente["token"], payload_chatwoot())
    await envia_webhook(http, agente["token"], payload_chatwoot())
    assert len(fila.jobs) == 1


async def test_reentrega_nao_reagenda_o_que_ja_foi_respondido(http, canal, fila, sessao, monkeypatch):
    agente, c = await conversa_com_pendencia(http, sessao, "Empresa A01c", "Agente A01c")
    sem_espera(monkeypatch)
    monkeypatch.setattr(turno, "_roda_com_tentativas", responde("Pronto"))
    assert await turno._turno(c.cliente_id, c.id, AsyncMock(return_value=True)) == "respondido"
    fila.jobs.clear()
    fila.chaves.clear()

    await envia_webhook(http, agente["token"], payload_chatwoot())
    assert fila.jobs == []


# A02: envio que não saiu não conta como respondido


async def test_envio_falho_deixa_a_entrada_pendente(http, canal, fila, sessao, monkeypatch):
    _, c = await conversa_com_pendencia(http, sessao, "Empresa A02", "Agente A02")
    sem_espera(monkeypatch)
    monkeypatch.setattr(turno, "_roda_com_tentativas", responde("Resposta"))
    monkeypatch.setattr(canal, "enviar_texto", AsyncMock(side_effect=ConnectionError("falha simulada")))

    assert await turno._turno(c.cliente_id, c.id, AsyncMock(return_value=True)) == "nao_enviado"
    async with sessao() as s:
        assert (await s.get(Conversa, c.id)).respondido_ate is None
        assert list(await s.scalars(select(Mensagem).where(Mensagem.autor == "agente"))) == []
        tipos = [f.tipo for f in await s.scalars(select(Falha))]
    assert "envio_falhou" in tipos


async def test_entrada_pendente_e_respondida_no_turno_seguinte(http, canal, fila, sessao, monkeypatch):
    _, c = await conversa_com_pendencia(http, sessao, "Empresa A02b", "Agente A02b")
    sem_espera(monkeypatch)
    monkeypatch.setattr(turno, "_roda_com_tentativas", responde("Resposta"))
    monkeypatch.setattr(canal, "enviar_texto", AsyncMock(side_effect=ConnectionError("falha simulada")))
    await turno._turno(c.cliente_id, c.id, AsyncMock(return_value=True))

    monkeypatch.undo()
    sem_espera(monkeypatch)
    monkeypatch.setattr(turno, "_roda_com_tentativas", responde("Resposta na segunda tentativa"))
    assert await turno._turno(c.cliente_id, c.id, AsyncMock(return_value=True)) == "respondido"
    assert canal.enviadas[-1][1] == "Resposta na segunda tentativa"


async def test_envio_parcial_registra_falha_e_nao_repete_o_que_saiu(
    http, canal, fila, sessao, monkeypatch
):
    _, c = await conversa_com_pendencia(http, sessao, "Empresa A02c", "Agente A02c")
    sem_espera(monkeypatch)
    monkeypatch.setattr(turno, "_roda_com_tentativas", responde("Primeira", "Segunda"))
    original = canal.enviar_texto

    async def cai_na_segunda(credenciais, conversa, texto):
        if texto == "Segunda":
            raise ConnectionError("falha simulada")
        return await original(credenciais, conversa, texto)

    monkeypatch.setattr(canal, "enviar_texto", cai_na_segunda)
    assert await turno._turno(c.cliente_id, c.id, AsyncMock(return_value=True)) == "respondido"
    async with sessao() as s:
        assert (await s.get(Conversa, c.id)).respondido_ate is not None
        tipos = [f.tipo for f in await s.scalars(select(Falha))]
    assert "resposta_incompleta" in tipos
    assert [t for _, t in canal.enviadas] == ["Primeira"]


# A03: prazo do token não é mensagem nova


async def test_token_vencido_ainda_responde(http, canal, fila, sessao, redis, monkeypatch):
    """Fila lenta ou modelo demorado não podem descartar a resposta: ninguém a refaria."""
    _, c = await conversa_com_pendencia(http, sessao, "Empresa A03", "Agente A03")
    sem_espera(monkeypatch)
    token = await buffer.agenda_turno(redis, c.cliente_id, c.id, 8)
    monkeypatch.setattr(turno, "_roda_com_tentativas", responde("Resposta"))
    await redis.delete(f"buffer:{c.id}")

    resultado = await turno.processar_turno({"redis": redis}, str(c.cliente_id), str(c.id), token)
    assert resultado == "respondido"
    assert canal.enviadas[-1][1] == "Resposta"


async def test_mensagem_nova_continua_descartando_o_turno_anterior(
    http, canal, fila, sessao, redis, monkeypatch
):
    _, c = await conversa_com_pendencia(http, sessao, "Empresa A03b", "Agente A03b")
    token = await buffer.agenda_turno(redis, c.cliente_id, c.id, 8)
    await buffer.agenda_turno(redis, c.cliente_id, c.id, 8)  # chegou outra mensagem

    resultado = await turno.processar_turno({"redis": redis}, str(c.cliente_id), str(c.id), token)
    assert resultado == "substituido"
    assert canal.enviadas == []


async def test_prazo_do_token_cobre_o_turno_inteiro():
    """80 segundos não cobriam fila, mídia e modelo; o prazo passa do lock com folga."""
    assert buffer.prazo_do_token(8) > config().lock_ttl_segundos


# A04: humano que assume cala o agente na hora


async def test_humano_durante_o_modelo_impede_a_resposta(http, canal, fila, sessao, monkeypatch):
    agente, c = await conversa_com_pendencia(http, sessao, "Empresa A04", "Agente A04")
    sem_espera(monkeypatch)

    async def modelo(*args, **kwargs):
        await envia_webhook(http, agente["token"], payload_chatwoot(
            mensagem_id=2, conteudo="Vou assumir", tipo="outgoing", remetente={"id": 7, "type": "user"},
        ))
        canal.status = "open"
        return ResultadoTurno(["Resposta depois da intervenção"])

    monkeypatch.setattr(turno, "_roda_com_tentativas", modelo)
    assert await turno._turno(c.cliente_id, c.id, AsyncMock(return_value=True)) == "nao_enviado"
    assert canal.enviadas == []
    async with sessao() as s:
        assert (await s.get(Conversa, c.id)).status == "humano"


async def test_humano_entre_duas_mensagens_para_o_resto(http, canal, fila, sessao, monkeypatch):
    agente, c = await conversa_com_pendencia(http, sessao, "Empresa A04b", "Agente A04b")
    sem_espera(monkeypatch)
    monkeypatch.setattr(turno, "_roda_com_tentativas", responde("Primeira", "Segunda", "Terceira"))
    original = canal.enviar_texto

    async def assume_depois_da_primeira(credenciais, conversa, texto):
        enviado = await original(credenciais, conversa, texto)
        if texto == "Primeira":
            await envia_webhook(http, agente["token"], payload_chatwoot(
                mensagem_id=3, conteudo="Assumo daqui", tipo="outgoing", remetente={"id": 7, "type": "user"},
            ))
            canal.status = "open"
        return enviado

    monkeypatch.setattr(canal, "enviar_texto", assume_depois_da_primeira)
    await turno._turno(c.cliente_id, c.id, AsyncMock(return_value=True))
    assert [t for _, t in canal.enviadas] == ["Primeira"]


# A05: prompt não passa de uma empresa para outra


async def test_empresa_nova_com_o_mesmo_nome_nao_herda_o_prompt(http, canal, fila):
    antiga = await cria_cliente_e_agente(http, "Empresa Repetida", "Agente Repetido")
    arquivo = config().diretorio_prompts / antiga["arquivo_prompt"]
    arquivo.write_text("INSTRUÇÕES DA EMPRESA ANTERIOR", encoding="utf-8")

    await http.request(
        "DELETE", f'/admin/clientes/{antiga["cliente_id"]}/agentes/{antiga["id"]}',
        headers=ADMIN, json={"confirmacao": "Agente Repetido"},
    )
    await http.request(
        "DELETE", f'/admin/clientes/{antiga["cliente_id"]}',
        headers=ADMIN, json={"confirmacao": "Empresa Repetida"},
    )

    nova = await cria_cliente_e_agente(http, "Empresa Repetida", "Agente Repetido")
    assert antiga["cliente_id"] != nova["cliente_id"]
    texto = (config().diretorio_prompts / nova["arquivo_prompt"]).read_text(encoding="utf-8")
    assert "INSTRUÇÕES DA EMPRESA ANTERIOR" not in texto
    assert "Agente Repetido" in texto


async def test_prompt_da_empresa_anterior_fica_guardado(http, canal, fila):
    antiga = await cria_cliente_e_agente(http, "Empresa Guardada", "Agente Guardado")
    (config().diretorio_prompts / antiga["arquivo_prompt"]).write_text("PROMPT ANTIGO", encoding="utf-8")
    await http.request(
        "DELETE", f'/admin/clientes/{antiga["cliente_id"]}/agentes/{antiga["id"]}',
        headers=ADMIN, json={"confirmacao": "Agente Guardado"},
    )
    await http.request(
        "DELETE", f'/admin/clientes/{antiga["cliente_id"]}',
        headers=ADMIN, json={"confirmacao": "Empresa Guardada"},
    )
    await cria_cliente_e_agente(http, "Empresa Guardada", "Agente Guardado")

    guardados = list(config().diretorio_prompts.glob("empresa-guardada-*/*/persona.md"))
    assert [g for g in guardados if g.read_text(encoding="utf-8") == "PROMPT ANTIGO"]


async def test_a_mesma_empresa_continua_com_o_prompt_dela(http, canal, fila):
    """Remover e recriar um agente dentro da mesma empresa não pode apagar o que foi escrito."""
    primeiro = await cria_cliente_e_agente(http, "Empresa Mantida", "Agente Mantido")
    arquivo = config().diretorio_prompts / primeiro["arquivo_prompt"]
    arquivo.write_text("PROMPT EDITADO PELO OPERADOR", encoding="utf-8")
    await http.request(
        "DELETE", f'/admin/clientes/{primeiro["cliente_id"]}/agentes/{primeiro["id"]}',
        headers=ADMIN, json={"confirmacao": "Agente Mantido"},
    )

    segundo = (
        await http.post(
            f'/admin/clientes/{primeiro["cliente_id"]}/agentes',
            json={"nome": "Agente Mantido", "canal": "nativo"},
            headers=ADMIN,
        )
    ).json()
    assert (config().diretorio_prompts / segundo["arquivo_prompt"]).read_text(
        encoding="utf-8"
    ) == "PROMPT EDITADO PELO OPERADOR"


# A06: exclusividade durante todo o efeito externo


def test_lock_dura_mais_que_o_job():
    """Com o lock vencendo antes do job, outro turno entrava na conversa com o primeiro vivo."""
    assert config().lock_ttl_segundos > Configuracao.job_timeout


async def test_turno_que_perdeu_o_lock_para_de_enviar(http, canal, fila, sessao, redis, monkeypatch):
    _, c = await conversa_com_pendencia(http, sessao, "Empresa A06", "Agente A06")
    sem_espera(monkeypatch)
    monkeypatch.setattr(turno, "_roda_com_tentativas", responde("Primeira", "Segunda"))
    token = await buffer.agenda_turno(redis, c.cliente_id, c.id, 8)
    await buffer.adquire_lock(redis, c.id, token, 60)
    original = canal.enviar_texto

    async def rouba_o_lock(credenciais, conversa, texto):
        enviado = await original(credenciais, conversa, texto)
        await redis.set(f"lock:{c.id}", "de-outro-turno")
        return enviado

    monkeypatch.setattr(canal, "enviar_texto", rouba_o_lock)
    await turno._turno(
        c.cliente_id, c.id, AsyncMock(return_value=True), lambda: buffer.lock_e_meu(redis, c.id, token)
    )
    assert [t for _, t in canal.enviadas] == ["Primeira"]
    await redis.delete(f"lock:{c.id}")
