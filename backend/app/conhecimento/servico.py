"""Regra da base de conhecimento: receber material, ingerir e buscar.

Quem recebe (rota, menu ou painel) não toca no banco nem no disco: chama daqui. A ingestão é um job
do worker, como todo trabalho que chama modelo: a requisição só grava o documento como
`processando` e enfileira.
"""

import hashlib
import uuid
from pathlib import Path
from typing import Any

import httpx
import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.agentes import repo as agentes_repo
from app.conhecimento import divisao, embeddings, extracao, repo
from app.conhecimento.modelos import Documento
from app.plataforma.config import config

log = structlog.get_logger()

LIMITE_DE_BYTES = 20 * 1024 * 1024
TIMEOUT_DO_SITE = 30.0
FERRAMENTA = "base_conhecimento"


class NaoEncontrado(ValueError):
    pass


class Conflito(ValueError):
    pass


class CampoInvalido(ValueError):
    pass


async def _agente(sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID) -> Any:
    agente = await agentes_repo.obter(sessao, cliente_id, agente_id)
    if agente is None:
        raise NaoEncontrado("agente não encontrado")
    return agente


def pasta(cliente_id: uuid.UUID, agente_id: uuid.UUID) -> Path:
    return config().diretorio_conhecimento / str(cliente_id) / str(agente_id)


async def recebe_arquivo(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    nome_arquivo: str,
    conteudo: bytes,
    tipo_mime: str,
    fila: Any = None,
) -> Documento:
    """Grava o arquivo no disco, cria o documento como `processando` e enfileira a ingestão."""
    await _agente(sessao, cliente_id, agente_id)
    if not conteudo:
        raise CampoInvalido("arquivo vazio")
    if len(conteudo) > LIMITE_DE_BYTES:
        raise CampoInvalido("arquivo maior que 20 MB; divida em partes menores")
    # O formato é conferido antes de gravar: recusar na hora é melhor que um documento com erro.
    extracao.formato(nome_arquivo, tipo_mime)
    digest = hashlib.sha256(conteudo).hexdigest()
    if await repo.por_hash(sessao, cliente_id, agente_id, digest) is not None:
        raise Conflito("este material já está na base deste agente")

    destino = pasta(cliente_id, agente_id)
    destino.mkdir(parents=True, exist_ok=True)
    caminho = destino / f"{digest[:16]}-{Path(nome_arquivo).name}"[:200]
    caminho.write_bytes(conteudo)
    documento = await repo.cria_documento(
        sessao, cliente_id, agente_id, Path(nome_arquivo).name, digest, tipo_mime, "documento", str(caminho)
    )
    await _enfileira(fila, documento)
    await sessao.refresh(documento)
    return documento


async def recebe_texto(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    texto: str,
    titulo: str = "",
    fila: Any = None,
) -> Documento:
    """Uma afirmação escrita no painel. Vira documento igual, sem arquivo no disco."""
    await _agente(sessao, cliente_id, agente_id)
    texto = texto.strip()
    if len(texto) < 3:
        raise CampoInvalido("escreva o que o agente precisa saber")
    digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    if await repo.por_hash(sessao, cliente_id, agente_id, digest) is not None:
        raise Conflito("este material já está na base deste agente")
    nome = titulo.strip() or " ".join(texto.split())[:60]
    documento = await repo.cria_documento(
        sessao, cliente_id, agente_id, nome, digest, "text/plain", "texto"
    )
    await _enfileira(fila, documento, texto=texto)
    await sessao.refresh(documento)
    return documento


async def recebe_site(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    url: str,
    fila: Any = None,
) -> Documento:
    """Lê a página agora e guarda o texto dela. Site que muda depois precisa ser enviado de novo."""
    await _agente(sessao, cliente_id, agente_id)
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        raise CampoInvalido("endereço inválido; comece com https://")
    try:
        async with httpx.AsyncClient(timeout=TIMEOUT_DO_SITE, follow_redirects=True) as http:
            resposta = await http.get(url, headers={"User-Agent": "AsimovAgentes/1.0"})
            resposta.raise_for_status()
            conteudo = resposta.content[:LIMITE_DE_BYTES]
    except httpx.HTTPError as erro:
        raise CampoInvalido("não consegui abrir essa página") from erro

    texto = extracao.limpa(extracao.de_html(conteudo))
    if len(texto) < 50:
        raise CampoInvalido("essa página não tem texto que dê para ensinar")
    digest = hashlib.sha256(texto.encode("utf-8")).hexdigest()
    if await repo.por_hash(sessao, cliente_id, agente_id, digest) is not None:
        raise Conflito("este material já está na base deste agente")
    documento = await repo.cria_documento(
        sessao, cliente_id, agente_id, url[:300], digest, "text/html", "site"
    )
    await _enfileira(fila, documento, texto=texto)
    await sessao.refresh(documento)
    return documento


async def _enfileira(fila: Any, documento: Documento, texto: str = "") -> None:
    """Sem fila (teste, ou API sem worker), a ingestão roda aqui mesmo."""
    if fila is None:
        from app.plataforma.banco import fabrica_sessao

        async with fabrica_sessao()() as s:
            await ingerir(s, documento.cliente_id, documento.id, texto)
        return
    await fila.enqueue_job(
        "ingerir_documento", str(documento.cliente_id), str(documento.id), texto
    )


async def ingerir(
    sessao: AsyncSession, cliente_id: uuid.UUID, documento_id: uuid.UUID, texto: str = ""
) -> str:
    """Extrai, divide, gera os vetores e grava. Devolve o status final do documento."""
    documento = await repo.obter(sessao, cliente_id, documento_id)
    if documento is None:
        return "removido"
    try:
        conteudo = texto
        if not conteudo:
            caminho = Path(documento.caminho_arquivo)
            if not caminho.exists():
                raise extracao.NaoDeuParaLer("o arquivo sumiu do disco; envie de novo")
            conteudo = extracao.texto_de(
                caminho.read_bytes(), documento.nome_arquivo, documento.tipo_mime
            )
        trechos = divisao.em_trechos(conteudo)
        if not trechos:
            raise extracao.NaoDeuParaLer("não achei texto nenhum neste material")
        vetores = await embeddings.gerar(trechos)
        await repo.grava_trechos(sessao, documento, list(zip(trechos, vetores, strict=True)))
    except (extracao.NaoDeuParaLer, embeddings.SemEmbeddings) as erro:
        await repo.marca(sessao, cliente_id, documento_id, "erro", erro=str(erro))
        log.info("documento_com_erro", documento_id=str(documento_id), erro=str(erro))
        return "erro"
    except Exception as erro:
        await repo.marca(sessao, cliente_id, documento_id, "erro", erro="falha ao processar o material")
        log.error("documento_falhou", documento_id=str(documento_id), erro=repr(erro))
        return "erro"
    await repo.marca(sessao, cliente_id, documento_id, "pronto", total_trechos=len(trechos))
    await liga_a_ferramenta(sessao, cliente_id, documento.agente_id)
    log.info("documento_pronto", documento_id=str(documento_id), trechos=len(trechos))
    return "pronto"


async def liga_a_ferramenta(
    sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID
) -> None:
    """Material pronto liga a busca no agente, se o operador ainda não tinha ligado.

    Sem isto, o operador sobe a tabela de preços, pergunta o preço e o agente responde que não sabe,
    porque a ferramenta estava desmarcada em outra aba. Desligar continua sendo dele, em Ferramentas.
    """
    agente = await agentes_repo.obter(sessao, cliente_id, agente_id)
    if agente is None or FERRAMENTA in (agente.ferramentas or []):
        return
    agente.ferramentas = [*(agente.ferramentas or []), FERRAMENTA]
    await sessao.commit()


async def remover(
    sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID, documento_id: uuid.UUID
) -> None:
    documento = await repo.obter(sessao, cliente_id, documento_id)
    if documento is None or documento.agente_id != agente_id:
        raise NaoEncontrado("material não encontrado")
    await repo.remove(sessao, cliente_id, documento)
    caminho = Path(documento.caminho_arquivo) if documento.caminho_arquivo else None
    if caminho is not None and caminho.exists():
        caminho.unlink(missing_ok=True)


async def buscar(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    agente_id: uuid.UUID,
    pergunta: str,
    quantos: int = 5,
) -> list[dict[str, Any]]:
    vetor = await embeddings.gerar([pergunta])
    return await repo.busca(sessao, cliente_id, agente_id, vetor[0], quantos)


async def tem_base(sessao: AsyncSession, cliente_id: uuid.UUID, agente_id: uuid.UUID) -> bool:
    documentos = await repo.listar(sessao, cliente_id, agente_id)
    return any(d.status == "pronto" for d in documentos)
