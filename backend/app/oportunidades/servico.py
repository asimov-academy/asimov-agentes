"""Regras do funil: o que pode existir, o que pode mudar e o que o quadro devolve.

A rota não orquestra nada daqui: ela recebe, valida o formato e chama uma destas funções.
"""

import uuid
from decimal import Decimal
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.oportunidades import repo
from app.oportunidades.modelos import EtapaFunil, Etiqueta, Oportunidade

# As cores são nomes de token da paleta do painel, nunca hexadecimal: cor solta na tela é proibida
# no projeto, e etiqueta fora da paleta estraga o quadro inteiro.
CORES = ("ciano", "ok", "atencao", "perigo", "muted")

# O funil que nasce com a empresa. Serve para o quadro abrir com colunas em vez de vazio, e o
# operador renomeia, remove e acrescenta o que quiser.
ETAPAS_INICIAIS = (
    ("Novo", False, False),
    ("Em conversa", False, False),
    ("Proposta", False, False),
    ("Ganho", True, False),
    ("Perdido", False, True),
)

LIMITE_DE_ETAPAS = 12


class NaoEncontrado(LookupError):
    pass


class CampoInvalido(ValueError):
    pass


class Conflito(ValueError):
    pass


async def garante_etapas(sessao: AsyncSession, cliente_id: uuid.UUID) -> list[EtapaFunil]:
    """Primeira visita ao quadro cria o funil padrão. Depois disso, nunca mais mexe."""
    existentes = await repo.etapas(sessao, cliente_id)
    if existentes:
        return existentes
    for ordem, (nome, ganha, perdida) in enumerate(ETAPAS_INICIAIS):
        await repo.cria_etapa(
            sessao,
            EtapaFunil(cliente_id=cliente_id, nome=nome, ordem=ordem, ganha=ganha, perdida=perdida),
        )
    await sessao.commit()
    return await repo.etapas(sessao, cliente_id)


async def quadro(sessao: AsyncSession, cliente_id: uuid.UUID) -> dict[str, Any]:
    """O kanban inteiro numa chamada: colunas, cartões e etiquetas.

    Uma chamada só porque o quadro não serve pela metade: coluna sem cartão e cartão sem coluna não
    desenham nada, e três chamadas em sequência piscam a tela.
    """
    etapas = await garante_etapas(sessao, cliente_id)
    etiquetas = await repo.etiquetas(sessao, cliente_id)
    cartoes = await repo.oportunidades(sessao, cliente_id)
    somas = await repo.total_por_etapa(sessao, cliente_id)

    return {
        "etapas": [
            {
                "id": str(e.id),
                "nome": e.nome,
                "ordem": e.ordem,
                "ganha": e.ganha,
                "perdida": e.perdida,
                "total": str(somas.get(e.id, Decimal("0"))),
            }
            for e in etapas
        ],
        "etiquetas": [
            {"id": str(e.id), "nome": e.nome, "cor": e.cor} for e in etiquetas
        ],
        "oportunidades": [
            {
                "id": str(c["oportunidade"].id),
                "etapa_id": str(c["oportunidade"].etapa_id),
                "titulo": c["oportunidade"].titulo,
                "valor": str(c["oportunidade"].valor),
                "nota": c["oportunidade"].nota,
                "ordem": c["oportunidade"].ordem,
                "contato_id": str(c["oportunidade"].contato_id) if c["oportunidade"].contato_id else None,
                "contato": c["contato_nome"] or c["contato_telefone"],
                "etiquetas": [str(i) for i in c["etiquetas"]],
                "criado_em": c["oportunidade"].criado_em.isoformat(),
            }
            for c in cartoes
        ],
    }


# Etapas


async def cria_etapa(sessao: AsyncSession, cliente_id: uuid.UUID, nome: str) -> EtapaFunil:
    nome = nome.strip()
    if not nome:
        raise CampoInvalido("a coluna precisa de um nome")
    atuais = await repo.etapas(sessao, cliente_id)
    if len(atuais) >= LIMITE_DE_ETAPAS:
        raise Conflito(f"o funil já tem {LIMITE_DE_ETAPAS} colunas; remova uma antes de criar outra")
    if any(e.nome.lower() == nome.lower() for e in atuais):
        raise Conflito(f"já existe uma coluna {nome!r}")
    etapa = await repo.cria_etapa(
        sessao,
        EtapaFunil(cliente_id=cliente_id, nome=nome, ordem=max((e.ordem for e in atuais), default=-1) + 1),
    )
    await sessao.commit()
    return etapa


async def renomeia_etapa(
    sessao: AsyncSession, cliente_id: uuid.UUID, etapa_id: uuid.UUID, nome: str
) -> EtapaFunil:
    etapa = await repo.etapa(sessao, cliente_id, etapa_id)
    if etapa is None:
        raise NaoEncontrado("coluna não encontrada")
    nome = nome.strip()
    if not nome:
        raise CampoInvalido("a coluna precisa de um nome")
    etapa.nome = nome
    await sessao.commit()
    return etapa


async def apaga_etapa(sessao: AsyncSession, cliente_id: uuid.UUID, etapa_id: uuid.UUID) -> None:
    """Coluna com cartão não some: o cartão iria junto, e ninguém quer descobrir isso depois."""
    etapa = await repo.etapa(sessao, cliente_id, etapa_id)
    if etapa is None:
        raise NaoEncontrado("coluna não encontrada")
    quantas = await repo.quantas_na_etapa(sessao, cliente_id, etapa_id)
    if quantas:
        raise Conflito(
            f"a coluna tem {quantas} {'oportunidade' if quantas == 1 else 'oportunidades'}; "
            "mova para outra coluna antes de remover"
        )
    await repo.apaga_etapa(sessao, cliente_id, etapa_id)
    await sessao.commit()


# Etiquetas


async def cria_etiqueta(
    sessao: AsyncSession, cliente_id: uuid.UUID, nome: str, cor: str
) -> Etiqueta:
    nome = nome.strip()
    if not nome:
        raise CampoInvalido("a etiqueta precisa de um nome")
    if cor not in CORES:
        raise CampoInvalido(f"cor desconhecida; use {', '.join(CORES)}")
    if any(e.nome.lower() == nome.lower() for e in await repo.etiquetas(sessao, cliente_id)):
        raise Conflito(f"já existe uma etiqueta {nome!r}")
    etiqueta = await repo.cria_etiqueta(
        sessao, Etiqueta(cliente_id=cliente_id, nome=nome, cor=cor)
    )
    await sessao.commit()
    return etiqueta


async def apaga_etiqueta(sessao: AsyncSession, cliente_id: uuid.UUID, etiqueta_id: uuid.UUID) -> None:
    """Some dos cartões junto, pelo `ON DELETE CASCADE` da ligação. É o que se espera de etiqueta."""
    if not await repo.apaga_etiqueta(sessao, cliente_id, etiqueta_id):
        raise NaoEncontrado("etiqueta não encontrada")
    await sessao.commit()


# Oportunidades


async def cria(
    sessao: AsyncSession,
    cliente_id: uuid.UUID,
    titulo: str,
    etapa_id: uuid.UUID | None = None,
    **campos: Any,
) -> Oportunidade:
    titulo = titulo.strip()
    if not titulo:
        raise CampoInvalido("a oportunidade precisa de um título")
    etapas = await garante_etapas(sessao, cliente_id)
    if etapa_id is None:
        destino = etapas[0]
    else:
        achada = await repo.etapa(sessao, cliente_id, etapa_id)
        if achada is None:
            raise NaoEncontrado("coluna não encontrada")
        destino = achada

    etiquetas = campos.pop("etiquetas", None)
    oportunidade = await repo.cria(
        sessao,
        Oportunidade(
            cliente_id=cliente_id,
            etapa_id=destino.id,
            titulo=titulo,
            ordem=await repo.proxima_ordem(sessao, cliente_id, destino.id),
            **{c: v for c, v in campos.items() if v is not None},
        ),
    )
    if etiquetas is not None:
        await _grava_etiquetas(sessao, cliente_id, oportunidade.id, etiquetas)
    await sessao.commit()
    return oportunidade


async def edita(
    sessao: AsyncSession, cliente_id: uuid.UUID, oportunidade_id: uuid.UUID, campos: dict[str, Any]
) -> Oportunidade:
    oportunidade = await repo.obter(sessao, cliente_id, oportunidade_id)
    if oportunidade is None:
        raise NaoEncontrado("oportunidade não encontrada")

    if "etapa_id" in campos and campos["etapa_id"] is not None:
        destino = await repo.etapa(sessao, cliente_id, uuid.UUID(str(campos["etapa_id"])))
        if destino is None:
            raise NaoEncontrado("coluna não encontrada")
        # Mudou de coluna: o cartão vai para o fim da nova, que é onde a mão espera encontrá-lo.
        if destino.id != oportunidade.etapa_id and "ordem" not in campos:
            oportunidade.ordem = await repo.proxima_ordem(sessao, cliente_id, destino.id)
        oportunidade.etapa_id = destino.id

    if "titulo" in campos:
        titulo = str(campos["titulo"]).strip()
        if not titulo:
            raise CampoInvalido("a oportunidade precisa de um título")
        oportunidade.titulo = titulo
    for campo in ("valor", "nota", "ordem", "contato_id"):
        if campo in campos:
            setattr(oportunidade, campo, campos[campo])
    if "etiquetas" in campos:
        await _grava_etiquetas(sessao, cliente_id, oportunidade.id, campos["etiquetas"] or [])

    await sessao.commit()
    return oportunidade


async def apaga(sessao: AsyncSession, cliente_id: uuid.UUID, oportunidade_id: uuid.UUID) -> None:
    if not await repo.apaga(sessao, cliente_id, oportunidade_id):
        raise NaoEncontrado("oportunidade não encontrada")
    await sessao.commit()


async def _grava_etiquetas(
    sessao: AsyncSession, cliente_id: uuid.UUID, oportunidade_id: uuid.UUID, ids: list[Any]
) -> None:
    """Etiqueta de outra empresa não cola: a busca já filtra por `cliente_id` e ela some da lista."""
    pedidas = [uuid.UUID(str(i)) for i in ids]
    validas = await repo.etiquetas_por_id(sessao, cliente_id, pedidas)
    await repo.troca_etiquetas(sessao, oportunidade_id, [e.id for e in validas])
