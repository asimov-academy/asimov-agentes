"""Divisão da resposta em mensagens curtas e quanto tempo o agente fica "digitando" cada uma."""

import random

DIGITANDO_MINIMO_SEGUNDOS = 1.0
VARIACAO = 0.15
"""Ninguém digita sempre no mesmo ritmo: cada mensagem varia até 15% para mais ou para menos."""


def limita_mensagens(mensagens: list[str], maximo: int) -> list[str]:
    """Nunca passa do máximo do agente: o excedente é juntado na última mensagem."""
    limpas = [m.strip() for m in mensagens if m and m.strip()]
    if len(limpas) <= maximo:
        return limpas
    return [*limpas[: maximo - 1], "\n\n".join(limpas[maximo - 1 :])]


def tempos_de_digitacao(
    textos: list[str],
    caracteres_por_segundo: int,
    maximo_segundos: int,
    ja_passou_segundos: float = 0.0,
    total_maximo_segundos: float = 90.0,
    sorteio: random.Random | None = None,
) -> list[float]:
    """Segundos de digitando antes de cada mensagem, como uma pessoa digitando no celular.

    Tempo = caracteres / velocidade, com variação, entre 1 s e o máximo do agente. O que o turno já
    levou (ler mídia, pensar a resposta) conta como digitação da primeira mensagem. A soma respeita
    `total_maximo_segundos`, que fica abaixo do lock da conversa.
    """
    sorteio = sorteio or random.Random()
    velocidade = max(caracteres_por_segundo, 1)
    tempos = [
        min(max(len(t) / velocidade * sorteio.uniform(1 - VARIACAO, 1 + VARIACAO), DIGITANDO_MINIMO_SEGUNDOS), maximo_segundos)
        for t in textos
    ]
    if tempos:
        tempos[0] = max(tempos[0] - ja_passou_segundos, DIGITANDO_MINIMO_SEGUNDOS)
    total = sum(tempos)
    if total > total_maximo_segundos:
        tempos = [t * total_maximo_segundos / total for t in tempos]
    return tempos
