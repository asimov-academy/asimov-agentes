"""Handoff: passar a conversa para humano e retomar quando ela volta.

Transferir: resumo com o modelo auxiliar, transferência no canal (nota, atribuição, pausa) e só
então o registro do Handoff aberto. Com handoff já aberto não faz nada: é idempotente.
Retomar: fecha o handoff aberto e devolve a conversa ao agente.
"""

import secrets
import time
import uuid
from datetime import timedelta
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.agentes import servico as agentes_servico
from app.consumo.modelos import Turno
from app.consumo.repo import grava_turno, registra_falha
from app.conversas import repo as conversas_repo
from app.handoff import repo
from app.handoff.modelos import Handoff
from app.ia.agente import conteudo, resume_conversa
from app.plataforma.banco import agora

if TYPE_CHECKING:
    from app.agentes.modelos import Agente
    from app.canais.base import Canal
    from app.conversas.modelos import Conversa, Mensagem

log = structlog.get_logger()

MENSAGEM_DE_EXPECTATIVA = (
    "Tive um problema para te responder agora. Já chamei uma pessoa da equipe, "
    "que vai continuar o atendimento por aqui."
)
MOTIVO_FALHA_NO_TURNO = "o agente não conseguiu responder (modelo ou tool com erro)"
MOTIVO_PESSOA_RESPONDEU = "uma pessoa da equipe respondeu pelo aparelho"
RESUMO_PESSOA_RESPONDEU = (
    "Sem resumo: a conversa foi assumida na hora, direto no WhatsApp, e o agente só ficou calado."
)
MOTIVO_ARQUIVO_GRANDE = "contato enviou arquivo grande ou longo demais para o agente abrir"

_LETRAS_DO_CODIGO = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def novo_codigo() -> str:
    return "".join(secrets.choice(_LETRAS_DO_CODIGO) for _ in range(6))


def nota_para_atendente(motivo: str, resumo: str) -> str:
    """Curta: o atendente lê no meio da conversa. O tamanho do resumo vem de `resumo_handoff.md`."""
    return f"Motivo: {motivo}\n{resumo}"


async def _resumo(
    sessao: AsyncSession,
    agente: "Agente",
    conversa_id: uuid.UUID,
    mensagens: list["Mensagem"],
    motivo: str,
) -> str:
    """Sem resumo do modelo, a nota leva as últimas falas do contato: o handoff não pode travar."""
    inicio = time.monotonic()
    try:
        resultado = await resume_conversa(agente, mensagens, motivo)
    except Exception as erro:
        await registra_falha(
            "resumo_handoff_falhou", {"erro": repr(erro)[:500]}, agente.cliente_id, agente.id
        )
        falas = [conteudo(m)[:300] for m in mensagens if m.autor == "contato"][-3:]
        return "Resumo automático indisponível. Últimas falas do contato:\n" + "\n".join(falas)
    await grava_turno(
        sessao,
        Turno(
            cliente_id=agente.cliente_id,
            conversa_id=conversa_id,
            modelo=agente.modelo_auxiliar,
            funcao="resumo_handoff",
            tokens_entrada=resultado.tokens_entrada,
            tokens_saida=resultado.tokens_saida,
            custo_estimado=resultado.custo_estimado,
            latencia_ms=int((time.monotonic() - inicio) * 1000),
        ),
    )
    return resultado.texto or "Resumo vazio."


async def transferir(
    sessao: AsyncSession,
    agente: "Agente",
    canal: "Canal",
    credenciais: dict[str, Any],
    conversa: "Conversa",
    motivo: str,
) -> str:
    """Devolve `transferido`, `desligado`, `ja_aberto` ou `falhou`. Quem chama faz o commit.

    Agente com `transfere_para_humano` desligado não transfere por caminho nenhum, nem pela tool
    (que nem é oferecida ao modelo), nem por falha no turno, nem por arquivo grande demais: quem
    desligou não tem equipe esperando do outro lado, e avisar que alguém vai assumir seria mentira.
    """
    if not agente.transfere_para_humano:
        log.info("handoff_desligado_no_agente", agente_id=str(agente.id), motivo=motivo)
        return "desligado"
    if await repo.aberto(sessao, agente.cliente_id, conversa.id) is not None:
        return "ja_aberto"

    mensagens = await conversas_repo.ultimas_mensagens(sessao, agente.cliente_id, conversa.id)
    resumo = await _resumo(sessao, agente, conversa.id, mensagens, motivo)
    quem = await como_chamar_o_contato(sessao, canal, conversa)
    # O código sai antes do aviso: nos canais diretos ele vai na mensagem que o destino recebe.
    codigo = novo_codigo()
    try:
        problemas = await canal.transferir(
            credenciais,
            conversa.id_externo,
            agente.handoff_destino,
            nota_para_atendente(motivo, resumo),
            codigo,
            quem,
        )
    except Exception as erro:
        await registra_falha("handoff_falhou", {"erro": repr(erro)[:500]}, agente.cliente_id, agente.id)
        return "falhou"
    if problemas:
        await registra_falha(
            "handoff_incompleto", {"problemas": problemas}, agente.cliente_id, agente.id
        )

    horas = agente.retomada_automatica_horas
    await repo.abre(
        sessao,
        Handoff(
            cliente_id=agente.cliente_id,
            agente_id=agente.id,
            conversa_id=conversa.id,
            motivo=motivo,
            resumo=resumo,
            codigo=codigo,
            destino=agente.handoff_destino,
            retomar_em=agora() + timedelta(hours=horas) if horas else None,
        ),
    )
    await conversas_repo.muda_status(sessao, agente.cliente_id, conversa.id, "humano")
    log.info("handoff_aberto", destino=(agente.handoff_destino or {}).get("tipo"))
    return "transferido"


async def pausar_por_humano(
    sessao: AsyncSession, agente: "Agente", conversa: "Conversa"
) -> bool:
    """Alguém da equipe respondeu pelo aparelho: o agente cala até o joinha ou o prazo.

    Chamado de dentro do webhook, então nada de IA nem de aviso: é só registrar a pausa. Com
    handoff já aberto não faz nada. Quem chama faz o commit.
    """
    if await repo.aberto(sessao, agente.cliente_id, conversa.id) is not None:
        return False
    horas = agente.retomada_automatica_horas
    await repo.abre(
        sessao,
        Handoff(
            cliente_id=agente.cliente_id,
            agente_id=agente.id,
            conversa_id=conversa.id,
            motivo=MOTIVO_PESSOA_RESPONDEU,
            resumo=RESUMO_PESSOA_RESPONDEU,
            codigo=novo_codigo(),
            destino=agente.handoff_destino,
            retomar_em=agora() + timedelta(hours=horas) if horas else None,
        ),
    )
    await conversas_repo.muda_status(sessao, agente.cliente_id, conversa.id, "humano")
    log.info("handoff_por_intervencao", agente_id=str(agente.id), horas=horas)
    return True


async def retomar(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID, por: str
) -> bool:
    """Fecha o handoff aberto e devolve a conversa ao agente. False se não havia handoff aberto."""
    fechou = await repo.fecha(sessao, cliente_id, conversa_id, por)
    await conversas_repo.muda_status(sessao, cliente_id, conversa_id, "agente")
    if fechou:
        log.info("handoff_retomado", por=por)
    return fechou


AVISO_DE_RETOMADA = "Pronto: o agente voltou a atender {contato}."
AVISO_DE_RETOMADA_POR_TEMPO = (
    "Passaram-se {horas} h e ninguém devolveu a conversa com {contato}: o agente voltou a atender."
)


async def retomar_por_codigo(
    sessao: AsyncSession, agente: "Agente", codigo: str | None
) -> bool:
    """`/retomar [código]` de quem recebeu o handoff. False quando não dá para saber qual conversa.

    O canal já conferiu de onde veio o comando; aqui se descobre qual conversa devolver. Sem
    código, vale a única conversa em atendimento: pedir um código quando não há dúvida é atrito à
    toa. Com mais de uma, o destino recebe a lista e escolhe.
    """
    canal, credenciais = _canal_do_agente(agente)
    if codigo:
        aberto = await repo.aberto_por_codigo(sessao, agente.cliente_id, agente.id, codigo)
    else:
        abertos = await repo.abertos_do_agente(sessao, agente.cliente_id, agente.id)
        if len(abertos) > 1:
            await _avisa(
                canal, credenciais, agente.handoff_destino, await _lista_para_escolher(sessao, canal, abertos)
            )
            return False
        aberto = abertos[0] if abertos else None
    if aberto is None:
        await _avisa(
            canal,
            credenciais,
            agente.handoff_destino,
            f"Não achei conversa em atendimento com o código {codigo.upper()}."
            " Confira o código no aviso que você recebeu."
            if codigo
            else "Nenhuma conversa em atendimento agora: o agente já está respondendo todas.",
        )
        return False
    conversa = await conversas_repo.obter_conversa(sessao, agente.cliente_id, aberto.conversa_id)
    await retomar(sessao, agente.cliente_id, aberto.conversa_id, "comando")
    await sessao.commit()
    await _avisa(
        canal,
        credenciais,
        agente.handoff_destino,
        AVISO_DE_RETOMADA.format(contato=await como_chamar_o_contato(sessao, canal, conversa)),
    )
    return True


ESPERA_APOS_FALHA_MINUTOS = 10


async def assumir_no_canal(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID, autor_externo: str | None
) -> bool:
    """Deixa à vista no canal que uma pessoa assumiu a conversa (no Chatwoot, aberta e atribuída).

    Roda no worker: o webhook só grava e agenda. Devolve se o canal foi avisado.
    """
    from app.agentes import repo as agentes_repo

    conversa = await conversas_repo.obter_conversa(sessao, cliente_id, conversa_id)
    if conversa is None:
        return False
    agente = await agentes_repo.obter(sessao, cliente_id, conversa.agente_id)
    if agente is None or agente.desligado:
        return False
    canal, credenciais = agentes_servico.canal_da_conversa(agente, conversa)
    try:
        await canal.assumir_no_canal(credenciais, conversa.id_externo, autor_externo)
    except Exception as erro:
        await registra_falha(
            "assumir_no_canal_falhou", {"erro": repr(erro)[:500]}, cliente_id, agente.id
        )
        return False
    return True


async def retomada_automatica(sessao: AsyncSession) -> int:
    """Devolve ao agente as conversas cujo prazo de handoff venceu. Roda de minuto em minuto.

    O canal é avisado primeiro (no Chatwoot, conversa de volta para pendente e sem atendente): se ele
    recusar, o handoff continua aberto e a tentativa fica para daqui a alguns minutos, senão o agente
    acharia que pode falar onde o canal não deixa. Falha só no aviso ao destino não impede a retomada.
    """
    from app.agentes import repo as agentes_repo

    retomadas = 0
    for aberto in await repo.vencidos(sessao, agora()):
        agente = await agentes_repo.obter(sessao, aberto.cliente_id, aberto.agente_id)
        if agente is None or agente.desligado:
            await repo.fecha(sessao, aberto.cliente_id, aberto.conversa_id, "tempo")
            await sessao.commit()
            continue
        conversa = await conversas_repo.obter_conversa(sessao, aberto.cliente_id, aberto.conversa_id)
        # Pelo canal da conversa, não pelo do agente: a conversa de teste no terminal é nativa até
        # em agente de Chatwoot ou WhatsApp, e devolver por lá não faria sentido nenhum
        # (auditoria de 2026-09-18, A10).
        canal, credenciais = (
            agentes_servico.canal_da_conversa(agente, conversa)
            if conversa is not None
            else _canal_do_agente(agente)
        )
        if conversa is not None and not await _devolve_no_canal(
            sessao, agente, canal, credenciais, conversa, aberto
        ):
            continue
        await retomar(sessao, aberto.cliente_id, aberto.conversa_id, "tempo")
        await sessao.commit()
        retomadas += 1
        await _avisa(
            canal,
            credenciais,
            aberto.destino or agente.handoff_destino,
            AVISO_DE_RETOMADA_POR_TEMPO.format(
                horas=agente.retomada_automatica_horas,
                contato=await como_chamar_o_contato(sessao, canal, conversa),
            ),
        )
    if retomadas:
        log.info("retomada_automatica", conversas=retomadas)
    return retomadas


async def _lista_para_escolher(
    sessao: AsyncSession, canal: "Canal", abertos: list[Handoff]
) -> str:
    """Com várias conversas em atendimento, só o código diz qual devolver."""
    linhas = []
    for aberto in abertos:
        conversa = await conversas_repo.obter_conversa(sessao, aberto.cliente_id, aberto.conversa_id)
        linhas.append(f"/retomar {aberto.codigo} para {await como_chamar_o_contato(sessao, canal, conversa)}")
    return "Tem mais de uma conversa em atendimento. Responda com o código da que você terminou:\n" + "\n".join(linhas)


async def _devolve_no_canal(
    sessao: AsyncSession,
    agente: "Agente",
    canal: "Canal",
    credenciais: dict[str, Any],
    conversa: "Conversa",
    aberto: Handoff,
) -> bool:
    """False quando o canal recusou: o handoff fica aberto e tenta de novo em alguns minutos."""
    try:
        await canal.devolver_ao_agente(credenciais, conversa.id_externo)
    except Exception as erro:
        await registra_falha(
            "retomada_no_canal_falhou", {"erro": repr(erro)[:500]}, agente.cliente_id, agente.id
        )
        aberto.retomar_em = agora() + timedelta(minutes=ESPERA_APOS_FALHA_MINUTOS)
        await sessao.commit()
        return False
    return True


def _canal_do_agente(agente: "Agente") -> tuple["Canal", dict[str, Any]]:
    """O canal do agente. Quando existe conversa, use `canal_da_conversa`: ela pode ser do
    terminal (nativa) mesmo num agente de canal externo."""
    from app.canais.registro import obter_canal

    return obter_canal(agente.canal), agentes_servico.credenciais(agente)


async def como_chamar_o_contato(
    sessao: AsyncSession, canal: "Canal", conversa: "Conversa | None"
) -> str:
    """Como o contato aparece para quem vai atender: nome e telefone, nessa ordem de preferência.

    O id da conversa pode ser um `@lid`, que é só um número interno do WhatsApp; mostrar isso como
    telefone num aviso faz a pessoa tentar ligar para um número que não existe.
    """
    if conversa is None:
        return "o contato"
    contato = await conversas_repo.obter_contato(sessao, conversa.cliente_id, conversa.contato_id)
    telefone = canal.rotulo_da_conversa(f"{contato.telefone}@c.us") if contato and contato.telefone else ""
    nome = (contato.nome or "").strip() if contato else ""
    if nome and telefone:
        return f"{nome} ({telefone})"
    return nome or telefone or canal.rotulo_da_conversa(conversa.id_externo)


async def _avisa(
    canal: "Canal", credenciais: dict[str, Any], destino: dict[str, Any] | None, texto: str
) -> None:
    try:
        await canal.avisa_destino(credenciais, destino, texto)
    except Exception as erro:
        log.warning("aviso_ao_destino_falhou", erro=repr(erro))


class ConversaNaoEncontrada(LookupError):
    pass


async def retomar_pelo_operador(
    sessao: AsyncSession, cliente_id: uuid.UUID, conversa_id: uuid.UUID
) -> bool:
    """Devolve a conversa no canal e fecha o handoff. False se não havia handoff aberto.

    Se o canal recusar, o handoff continua aberto: o agente não pode falar onde o canal não deixa.
    """
    conversa = await conversas_repo.obter_conversa(sessao, cliente_id, conversa_id)
    if conversa is None:
        raise ConversaNaoEncontrada("conversa não encontrada")
    agente = await agentes_repo.obter(sessao, cliente_id, conversa.agente_id)
    if agente is None:
        raise ConversaNaoEncontrada("o agente desta conversa foi removido")
    canal, credenciais = agentes_servico.canal_da_conversa(agente, conversa)
    await canal.devolver_ao_agente(credenciais, conversa.id_externo)
    fechou = await retomar(sessao, cliente_id, conversa_id, "operador")
    await sessao.commit()
    return fechou
