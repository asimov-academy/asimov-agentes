"""A cara do agente: a foto que o operador enviou, a do WhatsApp, ou a inicial numa cor.

O arquivo fica em `DIRETORIO_MIDIA/avatares/<cliente>/<agente>.<ext>`, junto do resto da mídia, e o
banco guarda só o caminho. Nada aqui devolve URL de fora: a foto do WhatsApp é baixada uma vez e
passa a ser um arquivo nosso, senão a lista do painel dependeria de um link que expira.

As cores são nomes de token do painel, nunca hexadecimal: quem pinta é o `tailwind.config.ts`.
"""

import asyncio
import hashlib
import uuid
from pathlib import Path
from typing import TYPE_CHECKING

import structlog

from app.plataforma.config import config

if TYPE_CHECKING:
    from app.agentes.modelos import Agente

log = structlog.get_logger()

PASTA = "avatares"
LIMITE_BYTES = 2 * 1024 * 1024
"""Foto de lista não precisa de mais que isso, e o que chega grande demais o operador recorta."""

TIPOS = {"image/png": "png", "image/jpeg": "jpg", "image/webp": "webp"}
"""Só o que todo navegador desenha. GIF e SVG ficam de fora: um anima na lista, o outro é código."""

CORES = ("ciano", "ok", "atencao", "texto")
"""Os tokens de cor do painel que servem de fundo para a inicial. Nenhum nome novo: quem pinta é o
`tailwind.config.ts`, e `perigo` fica de fora porque vermelho ali quer dizer outra coisa.

A ordem importa: é ela que decide a cor do agente que nunca escolheu uma."""


class ImagemRecusada(ValueError):
    """Tipo que não desenhamos, arquivo vazio ou acima do limite."""


def cor_de(agente: "Agente") -> str:
    """A cor escolhida, ou uma estável tirada do nome: o mesmo agente nunca troca de cor sozinho."""
    if agente.avatar_cor in CORES:
        return agente.avatar_cor
    digest = hashlib.sha256(agente.nome.strip().lower().encode()).digest()
    return CORES[digest[0] % len(CORES)]


def caminho_do_arquivo(agente: "Agente") -> Path | None:
    """O arquivo no disco, se houver foto e ela ainda existir."""
    if not agente.avatar:
        return None
    caminho = config().diretorio_midia / agente.avatar
    return caminho if caminho.is_file() else None


def _grava(destino: Path, conteudo: bytes) -> None:
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_bytes(conteudo)


def _apaga(caminho: Path) -> None:
    caminho.unlink(missing_ok=True)


async def guarda(agente: "Agente", conteudo: bytes, tipo_mime: str) -> str:
    """Grava a foto e devolve o caminho relativo. Quem chama faz o commit."""
    extensao = TIPOS.get(tipo_mime.split(";", 1)[0].strip().lower())
    if extensao is None:
        raise ImagemRecusada("a foto precisa ser PNG, JPEG ou WebP")
    if not conteudo:
        raise ImagemRecusada("o arquivo está vazio")
    if len(conteudo) > LIMITE_BYTES:
        raise ImagemRecusada(f"a foto passa de {LIMITE_BYTES // (1024 * 1024)} MB")

    anterior = caminho_do_arquivo(agente)
    # Nome novo a cada envio: o navegador guarda a foto pela URL, e trocar sem trocar o endereço
    # deixaria a antiga na tela até alguém limpar o cache.
    relativo = f"{PASTA}/{agente.cliente_id}/{agente.id}-{uuid.uuid4().hex[:8]}.{extensao}"
    await asyncio.to_thread(_grava, config().diretorio_midia / relativo, conteudo)
    agente.avatar = relativo
    if anterior is not None:
        await asyncio.to_thread(_apaga, anterior)
    return relativo


async def apaga(agente: "Agente") -> None:
    """Volta à inicial colorida. Quem chama faz o commit."""
    anterior = caminho_do_arquivo(agente)
    agente.avatar = ""
    if anterior is not None:
        await asyncio.to_thread(_apaga, anterior)


async def do_canal(agente: "Agente", credenciais: dict) -> bool:
    """Tenta trazer a foto do próprio número, no canal que souber dar uma.

    É melhor esforço, e só quando o agente ainda não tem foto: canal fora do ar, número sem foto ou
    WAHA antiga não podem atrapalhar quem acabou de parear o WhatsApp. Devolve se trouxe algo.
    """
    from app.canais.registro import obter_canal

    if agente.avatar:
        return False
    canal = obter_canal(agente.canal)
    buscar = getattr(canal, "foto_do_numero", None)
    if buscar is None:
        return False
    try:
        foto = await buscar(credenciais)
    except Exception as erro:
        log.info("avatar_do_canal_falhou", canal=agente.canal, erro=repr(erro)[:200])
        return False
    if foto is None:
        return False
    try:
        await guarda(agente, foto.conteudo, foto.tipo_mime)
    except ImagemRecusada as erro:
        log.info("avatar_do_canal_recusado", canal=agente.canal, motivo=str(erro))
        return False
    return True
