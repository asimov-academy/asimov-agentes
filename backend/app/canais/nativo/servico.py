"""Conversa de teste do operador com um agente, pelo terminal.

Vale para agente de qualquer canal: a conversa é criada no canal nativo e o turno responde por ele,
sem passar pelo canal do agente. Mandar grava a mensagem e agenda o buffer, como um webhook: a IA roda
só no worker. Ler devolve o que o agente mandou desde a última leitura, digitando, turno em andamento,
o último turno (tempo, tokens, custo, ferramentas) e o handoff aberto.
"""

import asyncio
import uuid
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.agentes.modelos import Agente
from app.canais.base import Anexo
from app.canais.nativo import memoria
from app.canais.nativo.canal import ID_CONTATO, PASTA_DE_ENVIOS, Nativo
from app.consumo import repo as consumo_repo
from app.conversas import buffer
from app.conversas import repo as conversas_repo
from app.conversas.modelos import Conversa, Mensagem
from app.handoff import repo as handoff_repo
from app.plataforma.config import config


class NaoEncontrado(LookupError):
    pass


class ArquivoRecusado(ValueError):
    """Arquivo vazio ou acima do limite de mídia da instalação."""


@dataclass(frozen=True)
class Arquivo:
    """O que o operador anexou na conversa de teste do painel."""

    nome: str
    conteudo: bytes
    tipo_mime: str


def _tipo(tipo_mime: str) -> str:
    """O mesmo vocabulário dos outros canais (`Anexo.tipo`). Quem decide se dá para ler é a mídia."""
    for prefixo, tipo in (("audio/", "audio"), ("image/", "imagem"), ("video/", "video")):
        if tipo_mime.startswith(prefixo):
            return tipo
    return "documento"


def _guarda(destino: Path, conteudo: bytes) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)


async def _anexa(arquivo: Arquivo) -> Anexo:
    """Guarda o arquivo onde o canal nativo vai buscá-lo no turno, como um canal externo guarda do
    lado dele. A leitura (transcrição, visão) acontece no worker, nunca aqui."""
    if not arquivo.conteudo:
        raise ArquivoRecusado("o arquivo está vazio")
    limite = config().midia_limite_bytes
    if len(arquivo.conteudo) > limite:
        raise ArquivoRecusado(f"o arquivo passa de {limite // (1024 * 1024)} MB")
    referencia = uuid.uuid4().hex
    await asyncio.to_thread(
        _guarda, config().diretorio_midia / PASTA_DE_ENVIOS / referencia, arquivo.conteudo
    )
    # `audio/webm;codecs=opus` do gravador do navegador: o parâmetro não é o tipo.
    tipo_mime = arquivo.tipo_mime.split(";", 1)[0].strip().lower() or "application/octet-stream"
    return Anexo(
        tipo=_tipo(tipo_mime),
        referencia=referencia,
        tipo_mime=tipo_mime,
        tamanho_bytes=len(arquivo.conteudo),
        nome=arquivo.nome[:200] or None,
    )


@dataclass(frozen=True)
class Enviada:
    conversa: str
    conversa_id: uuid.UUID
    agendada: bool
    """False com handoff aberto: a mensagem fica gravada e o agente não responde."""


@dataclass(frozen=True)
class Leitura:
    mensagens: list[dict[str, Any]]
    proxima: int
    digitando: bool
    respondendo: bool
    """Turno em andamento: resposta, handoff ou resumo ainda podem chegar."""
    turno: dict[str, Any] | None
    """Último turno de resposta da conversa."""
    handoff: dict[str, Any] | None


async def _agente(sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID) -> Agente:
    agente = await agentes_repo.obter(sessao, cliente_id, agente_id)
    # Em treinamento ele responde aqui, e é para isso que o treinamento serve.
    if agente is None or agente.desligado:
        raise NaoEncontrado("agente não encontrado")
    return agente


async def _conversa(
    sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID, conversa: str
) -> Conversa:
    encontrada = await conversas_repo.conversa_por_externo(sessao, cliente_id, agente_id, conversa)
    # Só conversa do terminal: nunca escrever numa conversa real do canal do agente.
    if encontrada is None or encontrada.canal != Nativo.nome:
        raise NaoEncontrado("conversa não encontrada")
    return encontrada


async def enviar(
    sessao: AsyncSession,
    fila: Any,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    texto: str,
    conversa: str | None,
    arquivo: Arquivo | None = None,
) -> Enviada:
    """Sem `conversa`, começa uma nova. Quem chama já validou o texto. Com `arquivo`, a mensagem
    leva o anexo, e o texto vira a legenda dele."""
    agente = await _agente(sessao, cliente_id, agente_id)
    anexo = await _anexa(arquivo) if arquivo is not None else None
    if conversa is None:
        contato = await conversas_repo.contato_do_canal(
            sessao, cliente_id, agente.id, ID_CONTATO, "Operador no terminal", None
        )
        atual = await conversas_repo.conversa_do_canal(
            sessao, cliente_id, agente.id, contato.id, uuid.uuid4().hex, Nativo.nome
        )
    else:
        atual = await _conversa(sessao, cliente_id, agente.id, conversa)

    await conversas_repo.grava_mensagem(
        sessao,
        Mensagem(
            cliente_id=cliente_id,
            conversa_id=atual.id,
            direcao="entrada",
            autor="contato",
            tipo=anexo.tipo if anexo else "texto",
            texto=texto or None,
            anexo=asdict(anexo) if anexo else None,
            id_externo=uuid.uuid4().hex,
        ),
    )
    await sessao.commit()

    agendada = atual.status != "humano"
    if agendada:
        await buffer.agenda_turno(fila, cliente_id, atual.id, agente.buffer_segundos)
    return Enviada(conversa=atual.id_externo, conversa_id=atual.id, agendada=agendada)


async def ler(
    sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID, conversa: str, depois: int
) -> Leitura:
    agente = await _agente(sessao, cliente_id, agente_id)
    atual = await _conversa(sessao, cliente_id, agente.id, conversa)
    # O lock primeiro: livre aqui, tudo que o turno gravou já está no Redis e no banco.
    async with memoria.conexao() as r:
        respondendo = await buffer.turno_em_andamento(r, atual.id)
    mensagens = await memoria.le_saida(atual.id_externo, depois)
    handoff = await handoff_repo.aberto(sessao, cliente_id, atual.id)
    turno = await consumo_repo.ultimo_turno(sessao, cliente_id, atual.id)
    return Leitura(
        mensagens=mensagens,
        proxima=depois + len(mensagens),
        digitando=await memoria.esta_digitando(atual.id_externo),
        respondendo=respondendo,
        turno=(
            {
                "id": str(turno.id),
                "modelo": turno.modelo,
                "latencia_ms": turno.latencia_ms,
                "tokens_entrada": turno.tokens_entrada,
                "tokens_saida": turno.tokens_saida,
                "custo_estimado": str(turno.custo_estimado) if turno.custo_estimado is not None else None,
                "ferramentas": turno.tools_chamadas or [],
                "erro": turno.erro,
            }
            if turno is not None
            else None
        ),
        handoff=(
            {"motivo": handoff.motivo, "resumo": handoff.resumo, "codigo": handoff.codigo}
            if handoff is not None
            else None
        ),
    )
