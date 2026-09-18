"""Mídia do contato dentro do turno: baixa, confere limites, usa o cache do cliente ou lê.

Cada anexo termina com uma `situacao` gravada no anexo da mensagem, e o modelo de resposta
recebe o resultado rotulado como dado do contato:
- `lido`: `texto_extraido` tem a transcrição ou a leitura;
- `acima_do_limite`: passou de 20 MB ou de 5 minutos de áudio e não foi lido;
- `nao_suportado`: tipo que o agente não lê (vídeo, planilha);
- `falhou`: download ou leitura quebrou; o agente pede para o contato escrever.

Nunca levanta: mídia com problema não derruba o turno.
"""

import asyncio
import hashlib
import time
import uuid
from dataclasses import fields
from datetime import timedelta
from enum import StrEnum
from pathlib import Path
from typing import TYPE_CHECKING, Any

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.canais.base import Anexo, ArquivoGrandeDemais
from app.consumo.modelos import Turno
from app.consumo.repo import grava_turno, registra_falha
from app.conversas import repo as conversas_repo
from app.ia.provedores import ModeloInvalido
from app.midia import extracao, repo
from app.midia.modelos import Midia
from app.plataforma.banco import agora
from app.plataforma.config import config

if TYPE_CHECKING:
    from app.agentes.modelos import Agente
    from app.canais.base import Canal
    from app.conversas.modelos import Mensagem

log = structlog.get_logger()

TENTATIVAS = 2
_espera = asyncio.sleep


class Situacao(StrEnum):
    LIDO = "lido"
    ACIMA_DO_LIMITE = "acima_do_limite"
    NAO_SUPORTADO = "nao_suportado"
    FALHOU = "falhou"


async def processa_pendentes(
    sessao: AsyncSession,
    agente: "Agente",
    canal: "Canal",
    credenciais: dict[str, Any],
    conversa_id: uuid.UUID,
    pendentes: list["Mensagem"],
) -> None:
    for mensagem in pendentes:
        if not mensagem.anexo or mensagem.anexo.get("situacao"):
            continue
        try:
            situacao, texto, midia_id = await _processa(
                sessao, agente, canal, credenciais, conversa_id, mensagem.anexo
            )
        except Exception as erro:
            await registra_falha(
                "midia_leitura_falhou", {"erro": repr(erro)[:500]}, agente.cliente_id, agente.id
            )
            situacao, texto, midia_id = Situacao.FALHOU, None, None
        await conversas_repo.registra_leitura_de_midia(
            sessao,
            agente.cliente_id,
            mensagem,
            {**mensagem.anexo, "situacao": str(situacao)},
            texto,
            midia_id,
        )
        log.info("midia_processada", tipo=mensagem.anexo.get("tipo"), situacao=str(situacao))


async def _processa(
    sessao: AsyncSession,
    agente: "Agente",
    canal: "Canal",
    credenciais: dict[str, Any],
    conversa_id: uuid.UUID,
    dados_anexo: dict[str, Any],
) -> tuple[Situacao, str | None, uuid.UUID | None]:
    cfg = config()
    anexo = Anexo(**{f.name: dados_anexo.get(f.name) for f in fields(Anexo)})
    detalhe = {"tipo": anexo.tipo}

    try:
        arquivo = await canal.baixar_midia(credenciais, anexo, cfg.midia_limite_bytes)
    except ArquivoGrandeDemais:
        await registra_falha(
            "midia_acima_do_limite", {**detalhe, "limite": "tamanho"}, agente.cliente_id, agente.id
        )
        return Situacao.ACIMA_DO_LIMITE, None, None
    except Exception as erro:
        await registra_falha(
            "midia_download_falhou", {**detalhe, "erro": repr(erro)[:500]}, agente.cliente_id, agente.id
        )
        return Situacao.FALHOU, None, None

    hash_sha256 = hashlib.sha256(arquivo.conteudo).hexdigest()
    guardada = await repo.por_hash(sessao, agente.cliente_id, hash_sha256)
    if guardada is not None:
        log.info("midia_do_cache")
        return Situacao.LIDO, guardada.resultado, guardada.id

    categoria = extracao.categoria(arquivo.tipo_mime)
    if categoria is None:
        return Situacao.NAO_SUPORTADO, None, None
    detalhe = {"tipo": categoria, "tipo_mime": arquivo.tipo_mime}

    if categoria == "audio":
        duracao = extracao.duracao_audio(arquivo.conteudo)
        if duracao is not None and duracao > cfg.midia_limite_audio_segundos:
            await registra_falha(
                "midia_acima_do_limite",
                {**detalhe, "limite": "duracao", "segundos": int(duracao)},
                agente.cliente_id,
                agente.id,
            )
            return Situacao.ACIMA_DO_LIMITE, None, None

    inicio = time.monotonic()
    try:
        lido = await _le_com_tentativas(agente, categoria, arquivo.conteudo, arquivo.tipo_mime)
    except extracao.MidiaNaoSuportada:
        return Situacao.NAO_SUPORTADO, None, None
    except Exception as erro:
        await registra_falha(
            "midia_leitura_falhou", {**detalhe, "erro": repr(erro)[:500]}, agente.cliente_id, agente.id
        )
        return Situacao.FALHOU, None, None
    latencia = int((time.monotonic() - inicio) * 1000)

    texto = lido.texto.strip()
    if not texto:
        await registra_falha(
            "midia_leitura_falhou", {**detalhe, "erro": "leitura vazia"}, agente.cliente_id, agente.id
        )
        return Situacao.FALHOU, None, None
    limite = cfg.midia_caracteres_extraidos
    if len(texto) > limite:
        texto = texto[:limite] + "\n(conteúdo cortado: arquivo longo)"

    caminho = Path(str(agente.cliente_id)) / str(agente.id) / hash_sha256
    await asyncio.to_thread(_salva, cfg.diretorio_midia / caminho, arquivo.conteudo)
    midia = await repo.grava(
        sessao,
        Midia(
            cliente_id=agente.cliente_id,
            hash_sha256=hash_sha256,
            tipo_mime=arquivo.tipo_mime,
            tamanho_bytes=len(arquivo.conteudo),
            caminho_arquivo=str(caminho),
            resultado=texto,
            metadados={**lido.metadados, "modelo": lido.modelo},
        ),
    )
    if lido.modelo:
        await grava_turno(
            sessao,
            Turno(
                cliente_id=agente.cliente_id,
                conversa_id=conversa_id,
                modelo=lido.modelo,
                funcao="transcricao" if categoria == "audio" else "visao",
                tokens_entrada=lido.tokens_entrada,
                tokens_saida=lido.tokens_saida,
                custo_estimado=lido.custo_estimado,
                latencia_ms=latencia,
            ),
        )
    return Situacao.LIDO, midia.resultado, midia.id


async def _le_com_tentativas(
    agente: "Agente", categoria: str, conteudo: bytes, tipo_mime: str
) -> extracao.Extracao:
    for tentativa in range(1, TENTATIVAS + 1):
        try:
            if categoria == "audio":
                return await extracao.transcrever(agente.modelo_transcricao, conteudo, tipo_mime)
            if categoria == "imagem":
                return await extracao.ler_imagem(agente.modelo_visao, conteudo, tipo_mime)
            return await extracao.ler_documento(agente.modelo_visao, conteudo, tipo_mime)
        except (extracao.MidiaNaoSuportada, ModeloInvalido):
            raise
        except Exception as erro:
            log.warning("leitura_de_midia_falhou", tentativa=tentativa, erro=repr(erro)[:300])
            if tentativa == TENTATIVAS:
                raise
            await _espera(2)
    raise AssertionError("inalcançável")


def _salva(destino: Path, conteudo: bytes) -> None:
    if destino.exists():
        return
    destino.parent.mkdir(parents=True, exist_ok=True)
    temporario = destino.with_suffix(".parcial")
    temporario.write_bytes(conteudo)
    temporario.replace(destino)


async def limpa_arquivos_antigos(sessao: AsyncSession) -> int:
    """Apaga do disco o arquivo que já virou texto. Devolve quantos saíram.

    O que a IA usa é o texto, guardado aqui e na mensagem; o arquivo é insumo e fica só o tempo de
    conferir um atendimento estranho. Registro e hash ficam: o cache continua valendo, e um arquivo
    reenviado não é lido de novo.
    """
    cfg = config()
    limite = agora() - timedelta(hours=cfg.midia_horas_no_disco)
    apagados = 0
    for midia in await repo.com_arquivo_antigo(sessao, limite):
        caminho = cfg.diretorio_midia / midia.caminho_arquivo
        try:
            await asyncio.to_thread(caminho.unlink, True)
        except OSError as erro:
            log.warning("midia_nao_apagada", erro=repr(erro), midia_id=str(midia.id))
            continue
        midia.arquivo_apagado_em = agora()
        apagados += 1
    if apagados:
        await sessao.commit()
        log.info("midia_limpa", arquivos=apagados, horas=cfg.midia_horas_no_disco)
    return apagados
