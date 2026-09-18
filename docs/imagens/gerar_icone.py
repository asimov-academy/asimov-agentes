#!/usr/bin/env python3
"""Gera o ícone quadrado do app da Meta: um A claro sobre fundo escuro.

Sem dependência: a borda suave sai da distância de cada pixel aos traços do A, e o PNG é escrito
com o zlib da biblioteca padrão. Rode com `python3 docs/imagens/gerar_icone.py`.
"""

import struct
import zlib
from pathlib import Path

LADO = 1024
FUNDO = (14, 17, 22)
LETRA = (255, 255, 255)

APICE = (512.0, 196.0)
BASE_ESQUERDA = (268.0, 836.0)
BASE_DIREITA = (756.0, 836.0)
TRAVESSA = ((374.0, 648.0), (650.0, 648.0))
GROSSURA = 96.0
GROSSURA_TRAVESSA = 86.0


def _distancia_do_traco(x: float, y: float, a: tuple[float, float], b: tuple[float, float]) -> float:
    """Distância do ponto ao segmento `a`-`b`, que é o que dá o traço com ponta arredondada."""
    dx, dy = b[0] - a[0], b[1] - a[1]
    comprimento = dx * dx + dy * dy
    quanto = 0.0 if comprimento == 0 else ((x - a[0]) * dx + (y - a[1]) * dy) / comprimento
    quanto = min(1.0, max(0.0, quanto))
    px, py = a[0] + quanto * dx, a[1] + quanto * dy
    return ((x - px) ** 2 + (y - py) ** 2) ** 0.5


TRACOS = (
    (BASE_ESQUERDA, APICE, GROSSURA),
    (APICE, BASE_DIREITA, GROSSURA),
    (TRAVESSA[0], TRAVESSA[1], GROSSURA_TRAVESSA),
)


def cobertura(x: float, y: float) -> float:
    """Quanto do pixel é letra, de 0 a 1. A faixa de 1 pixel na borda é o que suaviza o desenho."""
    melhor = 0.0
    for a, b, grossura in TRACOS:
        dentro = grossura / 2 - _distancia_do_traco(x, y, a, b)
        melhor = max(melhor, min(1.0, max(0.0, dentro + 0.5)))
        if melhor >= 1.0:
            return 1.0
    return melhor


def desenha() -> bytes:
    linhas = bytearray()
    for y in range(LADO):
        linhas.append(0)  # filtro da linha no PNG: nenhum
        centro_y = y + 0.5
        for x in range(LADO):
            quanto = cobertura(x + 0.5, centro_y)
            for fundo, letra in zip(FUNDO, LETRA):
                linhas.append(round(fundo + (letra - fundo) * quanto))
    return bytes(linhas)


def _pedaco(tipo: bytes, dados: bytes) -> bytes:
    return (
        struct.pack(">I", len(dados))
        + tipo
        + dados
        + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF)
    )


def png(pixels: bytes) -> bytes:
    cabecalho = struct.pack(">IIBBBBB", LADO, LADO, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _pedaco(b"IHDR", cabecalho)
        + _pedaco(b"IDAT", zlib.compress(pixels, 9))
        + _pedaco(b"IEND", b"")
    )


if __name__ == "__main__":
    destino = Path(__file__).with_name("icone-app.png")
    destino.write_bytes(png(desenha()))
    print(f"{destino} ({destino.stat().st_size // 1024} KB, {LADO}x{LADO})")
