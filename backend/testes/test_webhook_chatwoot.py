import json
import time

from sqlalchemy import func, select

from app.canais.chatwoot.assinatura import assinatura_confere, timestamp_recente
from app.consumo.modelos import Falha
from app.conversas.modelos import Mensagem
from app.main import app
from testes.conftest import BOT_ID, BOT_SECRET, FilaFalsa, cria_cliente_e_agente, envia_webhook, payload_chatwoot


async def _conta(sessao, modelo) -> int:  # type: ignore[no-untyped-def]
    async with sessao() as s:
        return await s.scalar(select(func.count()).select_from(modelo))


def test_assinatura_cobre_timestamp_e_corpo() -> None:
    import hashlib
    import hmac

    corpo = b'{"event":"message_created"}'
    ts = str(int(time.time()))
    so_corpo = "sha256=" + hmac.new(BOT_SECRET.encode(), corpo, hashlib.sha256).hexdigest()
    completa = "sha256=" + hmac.new(BOT_SECRET.encode(), f"{ts}.".encode() + corpo, hashlib.sha256).hexdigest()

    assert assinatura_confere(BOT_SECRET, ts, completa, corpo)
    assert not assinatura_confere(BOT_SECRET, ts, so_corpo, corpo)
    assert not assinatura_confere("outro-segredo", ts, completa, corpo)
    assert not timestamp_recente(str(int(time.time()) - 3600))


async def test_mensagem_valida_grava_e_agenda_buffer(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    resp = await envia_webhook(http, agente["token"], payload_chatwoot())

    assert resp.status_code == 200
    assert await _conta(sessao, Mensagem) == 1
    assert [j[0] for j in fila.jobs] == ["processar_turno"]


async def test_assinatura_invalida_responde_200_e_registra_falha(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    resp = await envia_webhook(http, agente["token"], payload_chatwoot(), secret="errado")

    assert resp.status_code == 200
    assert await _conta(sessao, Mensagem) == 0
    assert fila.jobs == []
    async with sessao() as s:
        assert await s.scalar(select(Falha.tipo)) == "webhook_assinatura_invalida"


async def test_reentrega_nao_duplica_mensagem_nem_turno(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    for _ in range(3):
        assert (await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=77))).status_code == 200

    assert await _conta(sessao, Mensagem) == 1
    assert len(fila.jobs) == 1


async def test_token_desconhecido_responde_200(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    resp = await envia_webhook(http, "token-que-nao-existe", payload_chatwoot())
    assert resp.status_code == 200
    assert fila.jobs == []


async def test_conversa_com_humano_grava_sem_agendar(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    await envia_webhook(http, agente["token"], payload_chatwoot(status="open"))

    assert await _conta(sessao, Mensagem) == 1
    assert fila.jobs == []


async def test_mensagem_do_proprio_agente_e_ignorada(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    await envia_webhook(http, agente["token"], payload_chatwoot(mensagem_id=1))

    propria = payload_chatwoot(mensagem_id=2, tipo="outgoing", remetente={"id": BOT_ID, "type": "agent_bot"})
    await envia_webhook(http, agente["token"], propria)

    assert await _conta(sessao, Mensagem) == 1


async def test_inbox_de_outro_agente_e_ignorada(http, canal, fila, sessao) -> None:  # type: ignore[no-untyped-def]
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    await envia_webhook(http, agente["token"], payload_chatwoot(inbox=99))

    assert await _conta(sessao, Mensagem) == 0


async def test_fila_fora_do_ar_responde_500(http, canal, sessao) -> None:  # type: ignore[no-untyped-def]
    app.state.fila = FilaFalsa(falhar=True)
    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")

    resp = await envia_webhook(http, agente["token"], payload_chatwoot())

    assert resp.status_code == 500


async def test_json_invalido_com_assinatura_valida_responde_200(http, canal, fila) -> None:  # type: ignore[no-untyped-def]
    from app.canais.chatwoot.assinatura import assina

    agente = await cria_cliente_e_agente(http, "Loja Exemplo", "Ana")
    corpo = b"nao e json"
    ts = str(int(time.time()))
    resp = await http.post(
        f"/webhook/chatwoot/{agente['token']}",
        content=corpo,
        headers={"X-Chatwoot-Timestamp": ts, "X-Chatwoot-Signature": assina(BOT_SECRET, corpo, ts)},
    )
    assert resp.status_code == 200
    assert json.dumps(fila.jobs) == "[]"
